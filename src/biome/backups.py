"""Verified documentary snapshots and restoration into a new catalogue."""
import hashlib
import json
import os
import shutil
import stat
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from diagnostics import diagnose_catalog
from storage import publish_directory

TECHNICAL = {'.local-session-token', '.workspace-settings.json', 'server-output.log', 'server-error.log'}


def existing_folder(value):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError('Choisissez un dossier existant avec le sélecteur.')
    path = Path(value)
    if path.is_symlink() or path.is_junction() or not path.is_dir():
        raise ValueError('Dossier inaccessible ou lien de dossier non pris en charge.')
    return path.resolve()


def inventory(root):
    files, directories = {}, []
    for folder, names, filenames in os.walk(root, followlinks=False, onerror=lambda e: (_ for _ in ()).throw(e)):
        parent = Path(folder)
        for name in names + filenames:
            path = parent / name
            if path.is_symlink() or path.is_junction():
                raise ValueError('Lien symbolique ou jonction dans le catalogue : ' + str(path.relative_to(root)))
        directories.extend((parent / name).relative_to(root).as_posix() for name in names)
        for name in filenames:
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if relative in TECHNICAL:
                continue
            info = path.stat()
            files[relative] = (info.st_size, info.st_mtime_ns)
    return files, sorted(directories)


def ready(root):
    report = diagnose_catalog(root)
    if report['errors']:
        raise ValueError('Le diagnostic signale des erreurs. Vérifiez les dossiers avant cette sauvegarde ou restauration.')
    if any('pending' in item['file'] or 'inachevée' in item['message'] for item in report['findings']):
        raise ValueError('Une opération est en attente dans le catalogue. Terminez sa reprise avant cette opération.')
    return report


def create_backup(source, destination):
    source = Path(source).resolve()
    target = existing_folder(destination)
    if target.is_relative_to(source):
        raise ValueError('Choisissez une destination en dehors du dossier de travail.')
    report = ready(source)
    before, directories = inventory(source)
    stamp = datetime.now().astimezone()
    identifier = uuid.uuid4().hex[:8]
    final = target / f'BIOME_backup_{stamp:%Y-%m-%d_%H%M%S}_{identifier}.zip'
    temporary = target / ('.backup-' + identifier + '.tmp')
    manifest = {'format': 'biome-documentary-backup', 'version': 1, 'created_at': stamp.isoformat(),
                'catalogue': source.name, 'projects': report['projects'],
                'external_references': report['external_references'], 'external_data_included': False,
                'directories': directories, 'files': {}}
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for relative, signature in sorted(before.items()):
                path = source / relative
                digest = hashlib.sha256()
                with path.open('rb') as original, archive.open('catalog/' + relative, 'w', force_zip64=True) as copied:
                    while chunk := original.read(1024 * 1024):
                        copied.write(chunk)
                        digest.update(chunk)
                info = path.stat()
                if (info.st_size, info.st_mtime_ns) != signature:
                    raise ValueError('Un fichier a changé pendant la sauvegarde. Réessayez après la fin des modifications.')
                manifest['files'][relative] = {'bytes': signature[0], 'sha256': digest.hexdigest()}
            if inventory(source) != (before, directories):
                raise ValueError('Le catalogue a changé pendant la sauvegarde ; copie non publiée.')
            archive.writestr('backup-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr('README.txt', 'BIOME documentary backup\n\nRestore with BIOME, or read catalog/ after extraction.\nExternal data are referenced, NOT included.\n')
        # Re-read the packed content, not just the source that was copied.
        with zipfile.ZipFile(temporary) as archive:
            for relative, expected in manifest['files'].items():
                digest = hashlib.sha256()
                with archive.open('catalog/' + relative) as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                if digest.hexdigest() != expected['sha256']:
                    raise ValueError('La vérification de la copie a échoué.')
        temporary.rename(final)
        return {'file': str(final), 'projects': report['projects'], 'files': len(before),
                'bytes': final.stat().st_size, 'external_references': report['external_references'],
                'external_data_included': False, 'warnings': report['warnings']}
    finally:
        if temporary.exists():
            temporary.unlink()


def safe_relative(name):
    if not isinstance(name, str) or not name or '\\' in name or name.startswith('/'):
        raise ValueError('Chemin invalide dans la sauvegarde.')
    parts = name.split('/')
    if any(part in ['', '.', '..'] or ':' in part or part.endswith((' ', '.')) for part in parts):
        raise ValueError('Chemin invalide dans la sauvegarde.')
    return name


def restore_backup(archive_path, destination):
    if not isinstance(archive_path, str) or not Path(archive_path).is_absolute():
        raise ValueError('Choisissez une sauvegarde ZIP.')
    original = Path(archive_path)
    if original.is_symlink() or not original.is_file():
        raise ValueError('Sauvegarde inaccessible.')
    target = existing_folder(destination)
    stamp = datetime.now().astimezone()
    identifier = uuid.uuid4().hex[:8]
    final = target / f'BIOME_restored_{stamp:%Y-%m-%d_%H%M%S}_{identifier}'
    stage = target / ('.restoring-' + identifier)
    try:
        with zipfile.ZipFile(original) as archive:
            names = archive.namelist()
            if len(names) != len(set(n.casefold() for n in names)):
                raise ValueError('La sauvegarde contient des chemins dupliqués.')
            try:
                info = archive.getinfo('backup-manifest.json')
                if info.file_size > 20_000_000:
                    raise ValueError('Inventaire trop volumineux.')
                manifest = json.loads(archive.read(info))
            except (KeyError, json.JSONDecodeError):
                raise ValueError('Ce ZIP ne contient pas un inventaire de sauvegarde BIOME valide.')
            if not isinstance(manifest, dict) or manifest.get('format') != 'biome-documentary-backup' or manifest.get('version') != 1:
                raise ValueError('Format de sauvegarde non pris en charge.')
            files = manifest.get('files')
            directories = manifest.get('directories')
            if not isinstance(files, dict) or not isinstance(directories, list):
                raise ValueError('Inventaire invalide.')
            required = {'backup-manifest.json', 'README.txt'} | {'catalog/' + safe_relative(n) for n in files}
            if set(names) != required:
                raise ValueError('Le contenu de la sauvegarde ne correspond pas à son inventaire.')
            total = 0
            for relative, expected in files.items():
                info = archive.getinfo('catalog/' + relative)
                if stat.S_ISLNK(info.external_attr >> 16) or not isinstance(expected, dict) or type(expected.get('bytes')) is not int or expected['bytes'] < 0 or not isinstance(expected.get('sha256'), str) or len(expected['sha256']) != 64:
                    raise ValueError('Enregistrement de fichier invalide.')
                if info.file_size != expected['bytes']:
                    raise ValueError('Taille différente de l’inventaire.')
                total += expected['bytes']
            if total > shutil.disk_usage(target).free:
                raise ValueError('Espace disque insuffisant pour la restauration.')
            stage.mkdir()
            for directory in directories:
                (stage / safe_relative(directory)).mkdir(parents=True, exist_ok=True)
            for relative, expected in files.items():
                path = stage / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with archive.open('catalog/' + relative) as stream, path.open('xb') as output:
                    while chunk := stream.read(1024 * 1024):
                        output.write(chunk)
                        digest.update(chunk)
                if digest.hexdigest() != expected['sha256']:
                    raise ValueError('Fichier altéré dans la sauvegarde : ' + relative)
            report = ready(stage)
            publish_directory(stage, final)
        return {'location': str(final), 'projects': report['projects'], 'files': len(files),
                'external_references': report['external_references'], 'warnings': report['warnings']}
    except zipfile.BadZipFile:
        raise ValueError('Archive ZIP illisible ou altérée.')
    finally:
        if stage.exists():
            # Only the freshly created temporary child may ever be removed.
            if stage.resolve().parent != target or not stage.name.startswith('.restoring-'):
                raise ValueError('Dossier temporaire inattendu ; suppression annulée.')
            shutil.rmtree(stage)
