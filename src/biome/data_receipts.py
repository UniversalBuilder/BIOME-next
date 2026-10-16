"""Stream and verify original data; preserve source files and portable locations."""
import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from storage import load, write_json, atomic, safe_file


def dataset_path(root, record):
    if record.get('storage') == 'project':
        return safe_file(root, record['location'])
    return Path(record['location'])


def write_companion(root, records):
    lines=['# Linked data', '', 'Locations and receipts; external data are not included automatically.', '']
    for item in records:
        lines += ['## '+item['name'], '', 'Role: '+item['role'], '',
                  'Storage: '+item.get('storage','external'), '', '```text',item['location'],'```','',item.get('description',''),'']
    atomic(root/'records/datasets.md','\n'.join(lines))


def source_inventory(value):
    if not isinstance(value,str) or not Path(value).is_absolute():
        raise ValueError('Choisissez un fichier ou un dossier local téléchargé.')
    source=Path(value)
    if source.is_symlink() or source.is_junction() or not source.exists():
        raise ValueError('Source inaccessible ou lien de dossier non pris en charge.')
    source=source.resolve()
    files={};directories=[]
    if source.is_file():
        stat=source.stat();files[source.name]=(stat.st_size,stat.st_mtime_ns)
    elif source.is_dir():
        for folder,names,filenames in os.walk(source,followlinks=False,onerror=lambda e: (_ for _ in ()).throw(e)):
            parent=Path(folder)
            for name in names+filenames:
                path=parent/name
                if path.is_symlink() or path.is_junction():
                    raise ValueError('La source contient un lien symbolique ou une jonction.')
            directories.extend((parent/name).relative_to(source).as_posix() for name in names)
            for name in filenames:
                path=parent/name;stat=path.stat()
                files[path.relative_to(source).as_posix()]=(stat.st_size,stat.st_mtime_ns)
    if not files:
        raise ValueError('La sélection ne contient aucun fichier.')
    signature=hashlib.sha256(json.dumps({'files':files,'directories':sorted(directories)},sort_keys=True).encode()).hexdigest()
    return source,files,sorted(directories),signature


def preview_receipt(source):
    path,files,_,signature=source_inventory(source)
    return {'source':str(path),'name':path.name,'files':len(files),
            'bytes':sum(value[0] for value in files.values()),'signature':signature}


def verify_files(folder, manifest):
    for item in manifest['files']:
        path=safe_file(folder,item['file'])
        if not path.is_file() or path.stat().st_size!=item['bytes']:
            raise ValueError('Un fichier de la réception est absent ou incomplet.')
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            while chunk:=stream.read(1024*1024): digest.update(chunk)
        if digest.hexdigest()!=item['sha256']:
            raise ValueError('Une copie de fichier ne correspond pas à sa source.')


def recover_receipt(root):
    pending=root/'records/pending-receipt.json'
    if not pending.exists(): return
    transaction=load(pending);record=transaction['record'];manifest=transaction['manifest']
    if record.get('storage') not in ['project','external'] or manifest.get('dataset_id')!=record.get('id') or record.get('receipt')!='records/receipts/'+record['id']+'.json':
        raise ValueError('Reçu de réception invalide.')
    if record['storage']=='project' and Path(record['location']).parent!=Path('data/original'):
        raise ValueError('Emplacement interne de réception invalide.')
    if record['storage']=='external' and not Path(record['location']).is_absolute():
        raise ValueError('Emplacement externe de réception invalide.')
    final=dataset_path(root,record)
    stage=Path(transaction['stage'])
    if stage.is_symlink() or stage.is_junction() or final.is_symlink() or final.is_junction():
        raise ValueError('Lien de dossier dans le journal de réception ; aucune copie déplacée.')
    identifier=record['id'].removeprefix('dataset-')
    if not re.fullmatch(r'[0-9a-f]{32}',identifier) or stage.name!='.receiving-'+identifier or stage.resolve().parent!=final.resolve().parent or not final.name.endswith(identifier[:8]):
        raise ValueError('Journal de réception invalide ; aucune copie déplacée.')
    if final.exists():
        if stage.exists(): raise ValueError('Deux copies de réception existent ; vérifiez les dossiers.')
        verify_files(final,manifest)
    else:
        verify_files(stage,manifest)
        stage.rename(final)
    receipts=root/'records/receipts';receipts.mkdir(exist_ok=True)
    write_json(root/record['receipt'],manifest)
    records=load(root/'records/datasets.json')
    existing=next((item for item in records if item['id']==record['id']),None)
    if existing is None: records.append(record)
    elif existing!=record: raise ValueError('La référence a été modifiée pendant la réception.')
    write_json(root/'records/datasets.json',records)
    write_companion(root,records)
    pending.unlink()


def receive_data(root,data):
    load(root/'biome.json')
    if data.get('storage')=='project' and (root.parent/'biome-catalogue.json').exists():
        raise ValueError('Dans ce catalogue, les originaux sont conservés dans un dossier de données séparé.')
    records=load(root/'records/datasets.json')
    if not isinstance(records,list) or any(not isinstance(item,dict) or not isinstance(item.get('id'),str) for item in records):
        raise ValueError('Le registre des données est invalide. Vérifiez le projet avant une réception.')
    pending=root/'records/pending-receipt.json'
    if pending.exists(): raise ValueError('Une réception précédente reste à finaliser.')
    mode=data.get('storage','project')
    if mode not in ['project','external']: raise ValueError('Destination non reconnue.')
    source,files,directories,signature=source_inventory(data.get('source'))
    if data.get('signature')!=signature:
        raise ValueError('La source a changé depuis la préparation. Préparez de nouveau la réception.')
    name=str(data.get('name','')).strip() or source.name
    if len(name)>300: raise ValueError('Nom trop long (300 caractères maximum).')
    provenance=str(data.get('provenance','')).strip()
    if len(provenance)>2000: raise ValueError('Provenance trop longue (2000 caractères maximum).')
    if mode=='project':
        parent=safe_file(root,'data/original')
    else:
        value=data.get('destination')
        if not isinstance(value,str) or not Path(value).is_absolute():
            raise ValueError('Choisissez un dossier durable de destination.')
        parent=Path(value)
        if parent.is_symlink() or parent.is_junction() or not parent.is_dir():
            raise ValueError('Destination inaccessible ou lien de dossier non pris en charge.')
        parent=parent.resolve()
        if parent.is_relative_to(root.resolve()):
            raise ValueError('Pour copier dans le projet, choisissez « Dans le projet ».')
    if source.is_dir() and parent.resolve().is_relative_to(source):
        raise ValueError('La destination ne peut pas être dans le dossier source.')
    # Find an existing ancestor before creating any directories.
    ancestor=parent
    while not ancestor.exists(): ancestor=ancestor.parent
    total=sum(info[0] for info in files.values())
    if total>shutil.disk_usage(ancestor).free: raise ValueError('Espace disque insuffisant pour cette copie.')
    parent.mkdir(parents=True,exist_ok=True)
    identifier=uuid.uuid4().hex;rid='dataset-'+identifier
    slug=re.sub(r'[^a-zA-Z0-9_-]+','-',source.stem if source.is_file() else source.name).strip('-')[:60] or 'received'
    final=parent/(slug+'_'+identifier[:8]);stage=parent/('.receiving-'+identifier)
    stage.mkdir()
    stamp=datetime.now().astimezone().isoformat()
    record={'id':rid,'name':name,'role':'original','storage':mode,
            'location':final.relative_to(root.resolve()).as_posix() if mode=='project' else str(final),
            'description':provenance,'created_at':stamp,'access_state':'verified',
            'receipt':'records/receipts/'+rid+'.json','file_count':len(files),'bytes':total}
    manifest={'format':'biome-data-receipt','version':1,'dataset_id':rid,'created_at':stamp,
              'source':str(source),'provenance':provenance,'storage':mode,'location':record['location'],'files':[]}
    try:
        for directory in directories: (stage/directory).mkdir(parents=True,exist_ok=True)
        for relative,expected in sorted(files.items()):
            original=source if source.is_file() else source/relative
            copied=stage/relative;copied.parent.mkdir(parents=True,exist_ok=True)
            digest=hashlib.sha256()
            with original.open('rb') as stream,copied.open('xb') as output:
                while chunk:=stream.read(1024*1024): output.write(chunk);digest.update(chunk)
            stat=original.stat()
            if (stat.st_size,stat.st_mtime_ns)!=expected:
                raise ValueError('Un original a changé pendant la copie. Réception non publiée.')
            manifest['files'].append({'file':relative,'bytes':expected[0],'sha256':digest.hexdigest()})
        if source_inventory(str(source))[3]!=signature:
            raise ValueError('Le dossier source a changé pendant la copie. Réception non publiée.')
        verify_files(stage,manifest)
        write_json(pending,{'record':record,'manifest':manifest,'stage':str(stage)})
        recover_receipt(root)
        return record
    finally:
        # After a persisted transaction, leave copies for safe recovery rather than deleting them.
        if stage.exists() and not pending.exists():
            if stage.resolve().parent!=parent.resolve() or stage.name!='.receiving-'+identifier:
                raise ValueError('Dossier temporaire inattendu ; nettoyage annulé.')
            shutil.rmtree(stage)
