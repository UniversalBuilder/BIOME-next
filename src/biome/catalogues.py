"""Explicit catalogue identity and safe creation; original data live elsewhere."""
from datetime import datetime
from pathlib import Path
import re
import uuid

from storage import load,write_json,publish_directory
from backups import existing_folder

MARKER='biome-catalogue.json'


def catalogue_info(location):
    root=existing_folder(str(location))
    if (root/'biome.json').exists():raise ValueError('Choisissez le catalogue, pas un projet individuel.')
    marker=root/MARKER
    if marker.is_symlink():raise ValueError('Identité du catalogue non valide.')
    if marker.exists():
        metadata=load(marker)
        if metadata.get('format')!='biome-catalogue' or metadata.get('version')!=1:
            raise ValueError('Format de catalogue non pris en charge.')
        if not isinstance(metadata.get('name'),str) or not metadata['name'].strip():raise ValueError('Nom de catalogue invalide.')
    else:metadata={'name':root.name,'id':None,'demo':False}
    projects=sum(1 for p in root.iterdir() if p.is_dir() and not p.name.startswith('.') and not p.is_symlink() and not p.is_junction() and (p/'biome.json').is_file())
    return {**metadata,'location':str(root),'projects':projects,'recognized':marker.exists() or projects>0,
            'documentary_only':True,'has_identity':marker.exists()}


def open_catalogue(location):
    info=catalogue_info(location)
    if not info['recognized']:
        raise ValueError('Ce dossier ne contient pas de catalogue BIOME. Utilisez « Créer un catalogue » pour en créer un nouveau.')
    return info


def create_catalogue(parent,name,demo=False):
    parent=existing_folder(parent)
    if not isinstance(name,str) or not name.strip() or len(name.strip())>100:
        raise ValueError('Saisissez un nom de catalogue de 1 à 100 caractères.')
    name=name.strip()
    if re.search(r'[<>:"/\\|?*\x00-\x1f]',name) or name.endswith(('.', ' ')) or name in ['.','..'] or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',name,re.I):
        raise ValueError('Ce nom ne convient pas pour un dossier Windows.')
    final=parent/name
    if final.exists():raise ValueError('Ce dossier existe déjà ; aucun contenu n’est remplacé.')
    stage=parent/('.creating-catalogue-'+uuid.uuid4().hex);stage.mkdir()
    write_json(stage/MARKER,{'format':'biome-catalogue','version':1,'id':str(uuid.uuid4()),
               'name':name,'created_at':datetime.now().astimezone().isoformat(),'demo':bool(demo),
               'storage_model':'documentary-catalogue-with-external-originals'})
    (stage/'README.txt').write_text('BIOME CATALOGUE\n\nThis folder contains project records, notebook entries, scripts, small attachments and delivery snapshots.\nOriginal scientific images are stored in separate data folders, linked from each project.\nBacking up this catalogue does not automatically back up external data.\nDo not put original image collections inside this folder.\n',encoding='utf-8')
    publish_directory(stage,final)
    return catalogue_info(final)


def remember_catalogue(settings,location):
    if settings is None:return
    settings=Path(settings)
    previous=load(settings) if settings.exists() else {}
    recent=previous.get('recent_catalogues',[])
    if previous.get('location'):recent=[previous['location'],*recent]
    recent=list(dict.fromkeys([str(location),*(p for p in recent if isinstance(p,str))]))[:8]
    write_json(settings,{**previous,'location':str(location),'recent_catalogues':recent})
