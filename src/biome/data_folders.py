"""Create identifiable, separate data folders without changing existing originals."""
from datetime import datetime
import hashlib
from pathlib import Path
import re
import unicodedata
import uuid
from storage import load, write_json
from data_receipts import write_companion

LAYOUT = ('01_raw', '02_processed', '03_results')


def slug(value, limit):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-zA-Z0-9]+', '-', value).strip('-')[:limit].rstrip('-')


def folder_info(root):
    project = load(root/'biome.json')
    date = str(project.get('created_at', ''))[:10]
    try: datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        match = re.match(r'^\d{4}-\d{2}-\d{2}', root.name)
        date = match[0] if match else 'undated'
    identity = hashlib.sha256(project['id'].encode()).hexdigest()[:8]
    parts = [date, slug(project.get('group'), 22), slug(project.get('contact'), 22), slug(project['title'], 48), identity]
    records = load(root/'records/datasets.json')
    structured = next((x for x in records if x.get('data_folder_root') and x.get('role')=='original'), None)
    return {'suggested_name': '_'.join(x for x in parts if x), 'layout': list(LAYOUT),
            'structured': structured, 'default_raw': structured['location'] if structured else None}


def checked_destination(root, parent, name):
    if not isinstance(parent, str) or not Path(parent).is_absolute():
        raise ValueError('Choisissez un dossier parent existant pour les données.')
    parent = Path(parent)
    if parent.is_symlink() or parent.is_junction() or not parent.is_dir():
        raise ValueError('Le dossier parent est inaccessible ou est un lien de dossier.')
    parent = parent.resolve()
    catalogue = root.resolve().parent
    if parent.is_relative_to(catalogue):
        raise ValueError('Choisissez un emplacement séparé du catalogue BIOME.')
    if not isinstance(name, str) or not name or name!=name.strip() or len(name)>180 or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith(('.', ' ')) or name in ['.', '..']:
        raise ValueError('Nom de dossier invalide (180 caractères maximum, sans séparateur ni caractère réservé).')
    if re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', name, re.I):
        raise ValueError('Ce nom est réservé par Windows.')
    target = parent/name
    if catalogue.is_relative_to(target):
        raise ValueError('Le dossier de données doit être séparé du catalogue BIOME.')
    if target.exists() or target.is_symlink() or target.is_junction():
        raise ValueError('Ce dossier existe déjà. Choisissez un autre nom ou liez le dossier existant.')
    if len(str(target))>225:
        raise ValueError('Le chemin est trop long. Raccourcissez le nom ou choisissez un dossier parent plus court.')
    return target


def create_data_folder(root, data):
    root=Path(root)
    info=folder_info(root)
    if info['structured']:
        raise ValueError('Ce projet possède déjà un dossier structuré. Ouvrez-le ou liez un autre emplacement si nécessaire.')
    target=checked_destination(root, data.get('parent'), data.get('name'))
    project=load(root/'biome.json');records=load(root/'records/datasets.json')
    if not isinstance(records,list):raise ValueError('Registre des données invalide.')
    # mkdir without exist_ok prevents adopting or overwriting an existing folder.
    target.mkdir()
    created=[]
    linked=False
    try:
        for name in LAYOUT:
            directory=target/name;directory.mkdir();created.append(directory)
        readme=target/'README.txt'
        with readme.open('x',encoding='utf-8') as stream:
            stream.write('BIOME — Project data / Données du projet\n\nProject / Projet: '+project['title']+'\nID: '+project['id']+'\nGroup / Groupe: '+str(project.get('group') or '—')+'\nContact: '+str(project.get('contact') or '—')+'\nCreated / Création du projet: '+str(project.get('created_at') or 'Unknown / Non renseignée')+'\n\n01_raw: original images; keep unchanged / images originales à conserver intactes.\n02_processed: transformed images and intermediate data / images transformées et données intermédiaires.\n03_results: analysis outputs / résultats d’analyse.\n\nNotes, attachments and deliveries remain in the separate BIOME catalogue.\nLe cahier, les pièces jointes et les livraisons restent dans le catalogue BIOME séparé.\nThis folder can be used without BIOME. / Ce dossier reste utilisable sans BIOME.\n')
        created.append(readme)
        item={'id':'dataset-'+uuid.uuid4().hex,'name':'Images originales — dossier du projet','role':'original',
              'storage':'external','location':str(target/'01_raw'),'data_folder_root':str(target),'folder_layout':1,
              'description':'Originaux dans 01_raw ; images transformées dans 02_processed ; résultats dans 03_results.',
              'access_state':'not_checked','created_at':datetime.now().astimezone().isoformat()}
        records.append(item)
        write_json(root/'records/datasets.json',records);linked=True
        write_companion(root,records)
        return item
    finally:
        if not linked:
            # Remove only the empty directories/files created by this call, never recursively.
            for path in reversed(created):
                try:
                    if path.is_dir():path.rmdir()
                    elif path.name=='README.txt':path.unlink()
                except OSError:pass
            try:target.rmdir()
            except OSError:pass


def project_data_path(root, identifier):
    item=next((x for x in load(root/'records/datasets.json') if x['id']==identifier),None)
    if not item or not item.get('data_folder_root'):
        raise ValueError('Dossier structuré introuvable.')
    parent=Path(item['data_folder_root'])
    if not parent.is_absolute() or Path(item['location'])!=parent/'01_raw':
        raise ValueError('Référence de dossier incohérente.')
    if not parent.is_dir():raise ValueError('Dossier de données inaccessible depuis cet ordinateur.')
    return parent
