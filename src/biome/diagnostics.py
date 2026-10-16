"""Read-only documentary checks; never recover files or probe external storage."""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from datetime import datetime
from pathlib import Path
from project_format import validate_project


def check_external(item):
    location = item['location']
    if location.lower().startswith(('http:', 'https:')):
        return {**item, 'state': 'unsupported', 'detail': 'Lien web : contrôle des pages web non disponible'}
    if not Path(location).is_absolute():
        return {**item, 'state': 'unsupported', 'detail': 'Choisir un chemin complet pour vérifier cet emplacement'}
    try:
        result = subprocess.run(([sys.executable,'--probe-location'] if getattr(sys,'frozen',False) else [sys.executable, str(Path(__file__).with_name('check_location.py'))]),
                                input=json.dumps({'location': location}), capture_output=True,
                                text=True, encoding='utf-8', timeout=3,
                                creationflags=0x08000000 if sys.platform == 'win32' else 0)
        if result.returncode:
            raise ValueError('Probe failed')
        return {**item, **json.loads(result.stdout)}
    except subprocess.TimeoutExpired:
        return {**item, 'state': 'timeout', 'detail': 'Pas de réponse sous 3 secondes ; réessayer après connexion au réseau ou au VPN'}
    except (OSError, ValueError):
        return {**item, 'state': 'unavailable', 'detail': 'La vérification d’accès n’a pas pu aboutir'}


def diagnose_catalog(folder, check_locations=False, progress=None):
    folder = Path(folder)
    findings = []
    projects = 0
    external = 0
    locations = []

    def issue(level, project, file, message):
        findings.append({'level': level, 'project': project, 'file': file, 'message': message})

    def read(root, relative, expected, project, required=True):
        path = root / relative
        if path.is_symlink() or any(p.is_symlink() or p.is_junction() for p in path.parents if p != root.parent and p.is_relative_to(root)):
            issue('error', project, relative, 'Lien de fichiers non pris en charge ; contenu non lu.')
            return None
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(value, expected):
                raise ValueError('structure')
            return value
        except FileNotFoundError:
            if required:
                issue('error', project, relative, 'Fichier nécessaire absent.')
        except (OSError, ValueError, UnicodeError):
            issue('error', project, relative, 'Fichier illisible ou structure JSON invalide.')
        return None

    def internal(root, relative, project, folder_allowed=False):
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            issue('error', project, str(relative), 'Lien interne invalide.')
            return
        path = root / relative
        if '..' in Path(relative).parts:
            issue('error', project, relative, 'Lien sortant du dossier projet.')
            return
        # Check components before resolution: do not follow a junction to a NAS.
        for part in [path, *path.parents]:
            if part == root:
                break
            if part.is_symlink() or part.is_junction():
                issue('error', project, relative, 'Lien symbolique ou jonction : accès non effectué.')
                return
        if not path.is_file() and not (folder_allowed and path.is_dir()):
            issue('error', project, relative, 'Fichier interne lié absent ou inaccessible.')

    def records(value, project, file):
        if value is None:
            return []
        result = []
        seen = set()
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']:
                issue('error', project, file, 'Enregistrement sans identifiant valide.')
                continue
            if item['id'] in seen:
                issue('error', project, file, 'Identifiant présent plusieurs fois : ' + item['id'])
            seen.add(item['id'])
            result.append(item)
        return result

    try:
        children = sorted(folder.iterdir())
    except OSError:
        issue('error', 'Dossier de travail', '', 'Dossier inaccessible.')
        children = []
    directory = read(folder, '.biome-directory.json', dict, 'Annuaire', required=False)
    for kind in ['contacts', 'groups']:
        if directory is not None:
            value = directory.get(kind)
            if not isinstance(value, list):
                issue('error', 'Annuaire', '.biome-directory.json', 'Liste invalide : ' + kind)
            else:
                records(value, 'Annuaire', '.biome-directory.json')
    vocab = read(folder, '.biome-vocabularies.json', dict, 'Listes', required=False)
    if vocab is not None:
        for kind in ['software', 'modalities', 'topics']:
            if not isinstance(vocab.get(kind), list):
                issue('error', 'Listes', '.biome-vocabularies.json', 'Liste invalide : ' + kind)
            else:
                records(vocab[kind], 'Listes', '.biome-vocabularies.json')
    for name in ['.biome-directory-pending.json', '.biome-vocabularies-pending.json']:
        if (folder / name).exists():
            issue('warning', 'Dossier de travail', name, 'Opération en attente ; aucune reprise effectuée par ce diagnostic.')
    project_ids = set()
    for root in children:
        if root.is_symlink() or root.is_junction():
            issue('warning', root.name, '', 'Lien de dossier ignoré.')
            continue
        if not root.is_dir():
            continue
        if root.name.startswith('.creating-'):
            issue('warning', root.name, '', 'Création inachevée possible ; dossier conservé.')
            continue
        if not (root / 'biome.json').exists() and not (root / 'records').is_dir():
            continue
        projects += 1
        name = root.name
        metadata = read(root, 'biome.json', dict, name)
        if metadata:
            pid = metadata.get('id')
            if not isinstance(pid, str) or not pid:
                issue('error', name, 'biome.json', 'Identifiant de projet absent ou invalide.')
            elif pid in project_ids:
                issue('error', name, 'biome.json', 'Identifiant partagé par plusieurs dossiers projets.')
            project_ids.add(str(pid))
            try:
                validate_project(metadata)
            except ValueError as error:
                issue('error', name, 'biome.json', str(error))
            if not isinstance(metadata.get('status'), dict) or metadata['status'].get('value') not in ['Intake', 'Active', 'Review', 'Completed', 'OnHold', 'Unknown']:
                issue('error', name, 'biome.json', 'Statut invalide.')
            for field in ['title']:
                if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                    issue('error', name, 'biome.json', 'Information nécessaire absente : ' + field)
            if directory:
                for kind, key in [('contacts', 'contact_id'), ('groups', 'group_id')]:
                    known = {x['id'] for x in directory.get(kind, []) if isinstance(x, dict) and isinstance(x.get('id'), str)} if isinstance(directory.get(kind), list) else set()
                    if metadata.get(key) and (not isinstance(metadata[key], str) or metadata[key] not in known):
                        issue('warning', name, 'biome.json', 'Identité absente de l’annuaire : ' + key)
        entries = records(read(root, 'records/entries.json', list, name), name, 'records/entries.json')
        versions = records(read(root, 'records/versions.json', list, name), name, 'records/versions.json')
        versions_by_id = {x['id']: x for x in versions}
        for item in entries:
            internal(root, item.get('file'), name)
            try:
                datetime.strptime(item.get('date_source', ''), '%d/%m/%Y %H:%M:%S')
            except (ValueError, TypeError):
                issue('error', name, 'records/entries.json', 'Date de note invalide : ' + item['id'])
            links = item.get('linked_file_ids', [])
            if not isinstance(links, list) or any(not isinstance(x, str) or x not in versions_by_id for x in links):
                issue('error', name, 'records/entries.json', 'Lien de pièce jointe sans enregistrement correspondant.')
        for item in versions:
            internal(root, item.get('file'), name)
        work = read(root, 'records/work-logs.json', dict, name)
        logs = []
        if work is not None:
            if not isinstance(work.get('logs'), list):
                issue('error', name, 'records/work-logs.json', 'Liste des séances invalide.')
            else:
                logs = records(work['logs'], name, 'records/work-logs.json')
        entry_ids = {x['id'] for x in entries}
        timed = Counter()
        for log in logs:
            if type(log.get('minutes')) is not int or not 0 <= log['minutes'] <= 1440:
                issue('error', name, 'records/work-logs.json', 'Durée invalide : ' + log['id'])
            try:
                datetime.strptime(log.get('date', ''), '%Y-%m-%d')
            except (ValueError, TypeError):
                issue('error', name, 'records/work-logs.json', 'Date de séance invalide : ' + log['id'])
            links = log.get('entry_ids')
            if not isinstance(links, list) or any(not isinstance(x, str) or x not in entry_ids for x in links):
                issue('error', name, 'records/work-logs.json', 'Séance reliée à une note inconnue.')
            else:
                timed.update(set(links))
        if any(count > 1 for count in timed.values()):
            issue('warning', name, 'records/work-logs.json', 'Plusieurs saisies de temps reliées à la même note ; vérifier le comptage.')
        datasets = records(read(root, 'records/datasets.json', list, name), name, 'records/datasets.json')
        for dataset in datasets:
            if dataset.get('storage')=='project':
                internal(root,dataset.get('location'),name,folder_allowed=True)
                if dataset.get('receipt'):
                    receipt=read(root,dataset['receipt'],dict,name)
                    if receipt is not None:
                        if not isinstance(receipt.get('files'),list):
                            issue('error',name,dataset['receipt'],'Liste des fichiers reçus invalide.')
                        else:
                            for item in receipt['files']:
                                if not isinstance(item,dict) or not isinstance(item.get('file'),str):
                                    issue('error',name,dataset['receipt'],'Fichier reçu invalide.')
                                else:
                                    internal(root,str(dataset.get('location',''))+'/'+item['file'],name)
                continue
            external += 1
            if not isinstance(dataset.get('location'), str) or not dataset['location'].strip():
                issue('error', name, 'records/datasets.json', 'Emplacement externe non renseigné.')
            else:
                locations.append({'project': name, 'name': dataset.get('name', dataset['id']), 'location': dataset['location']})
        deliveries = records(read(root, 'records/deliveries.json', list, name), name, 'records/deliveries.json')
        for delivery in deliveries:
            internal(root, delivery.get('file'), name)
        for pending in ['pending-entry.json', 'pending-info.json', 'pending-framing.json', 'pending-receipt.json']:
            if (root / 'records' / pending).exists():
                issue('warning', name, 'records/' + pending, 'Opération en attente ; fichier laissé intact.')
        data_folder=root/'data';originals=data_folder/'original'
        if not data_folder.is_symlink() and not data_folder.is_junction() and not originals.is_symlink() and not originals.is_junction() and originals.is_dir():
            try:
                for child in originals.iterdir():
                    if child.name.startswith('.receiving-'):
                        issue('warning',name,'data/original/'+child.name,'Copie de réception inachevée possible ; contenu conservé.')
            except OSError:
                issue('warning',name,'data/original','Le dossier des originaux ne peut pas être entièrement consulté.')
    results = []
    if check_locations:
        results=[None]*len(locations)
        if progress:progress(0,len(locations))
        with ThreadPoolExecutor(max_workers=4) as pool:
            pending={pool.submit(check_external,item):index for index,item in enumerate(locations)}
            completed=0
            for future in as_completed(pending):
                results[pending[future]]=future.result();completed+=1
                if progress:progress(completed,len(locations))
        for item in results:
            if item['state'] != 'accessible':
                issue('warning', item['project'], str(item['name']), item['detail'])
    counts = Counter(x['level'] for x in findings)
    return {'projects': projects, 'errors': counts['error'], 'warnings': counts['warning'],
            'external_references': external, 'locations': results, 'findings': findings,
            'scope': 'Informations du projet, dates et durées des séances, liens vers les notes et pièces jointes, présence des livraisons enregistrées.'}
