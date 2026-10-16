"""Recoverable project removal and verified catalogue relocation."""
import hashlib
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from backups import existing_folder,inventory,ready
from storage import load,write_json


def trash_project(catalogue,project):
    catalogue=existing_folder(str(catalogue));project=Path(project)
    if project.is_symlink() or project.is_junction() or project.resolve().parent!=catalogue:
        raise ValueError('Le projet doit appartenir directement au catalogue courant.')
    metadata=load(project/'biome.json')
    parent=catalogue/'.trash'
    if parent.is_symlink() or parent.is_junction():raise ValueError('Corbeille non valide.')
    parent.mkdir(exist_ok=True);identifier=uuid.uuid4().hex;folder=parent/identifier;folder.mkdir()
    receipt={'id':identifier,'folder':project.name,'title':metadata['title'],
             'deleted_at':datetime.now().astimezone().isoformat(),'project_id':metadata['id']}
    write_json(folder/'receipt.json',receipt)
    project.rename(folder/'project')
    return receipt


def trash_contents(catalogue):
    parent=Path(catalogue)/'.trash'
    if parent.is_symlink() or parent.is_junction():raise ValueError('Corbeille non valide.')
    items=[]
    if not parent.exists():return items
    for folder in parent.iterdir():
        if folder.is_symlink() or folder.is_junction() or not folder.is_dir():continue
        receipt=folder/'receipt.json'
        if receipt.is_symlink():continue
        if receipt.is_file() and (folder/'project/biome.json').is_file():
            item=load(receipt)
            if item.get('id')==folder.name:items.append(item)
    return sorted(items,key=lambda item:item['deleted_at'],reverse=True)


def restore_project(catalogue,identifier):
    catalogue=existing_folder(str(catalogue))
    item=next((item for item in trash_contents(catalogue) if item['id']==identifier),None)
    if item is None:raise ValueError('Projet absent de la corbeille.')
    name=item['folder']
    if Path(name).name!=name or name in ['.','..']:raise ValueError('Nom de dossier invalide.')
    target=catalogue/name;source=catalogue/'.trash'/identifier/'project'
    if source.is_symlink() or source.is_junction():raise ValueError('Projet non valide.')
    if target.exists():raise ValueError('Un dossier de ce nom existe déjà ; aucun remplacement.')
    source.rename(target)
    return {'title':item['title'],'location':str(target)}


def file_hash(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024):value.update(chunk)
    return value.hexdigest()


def relocate_catalogue(catalogue,parent):
    source=existing_folder(str(catalogue));parent=existing_folder(parent)
    if parent.is_relative_to(source) or source.is_relative_to(parent):
        raise ValueError('Choisissez un dossier séparé du catalogue et de ses dossiers parents.')
    final=parent/source.name
    if final.exists():raise ValueError('Un dossier portant ce nom existe déjà à destination.')
    report=ready(source);before=inventory(source)
    temporary=parent/('.moving-'+uuid.uuid4().hex)
    shutil.copytree(source,temporary)
    for relative in before[0]:
        if file_hash(source/relative)!=file_hash(temporary/relative):raise ValueError('La copie diffère de l’original ; catalogue actuel conservé.')
    if inventory(source)!=before or inventory(temporary)!=before:
        raise ValueError('Le catalogue a changé pendant la copie ; catalogue actuel conservé.')
    ready(temporary)
    write_json(temporary/'.relocation.json',{'source':str(source),'created_at':datetime.now().astimezone().isoformat(),
               'source_retained':True,'files_verified':len(before[0])})
    temporary.rename(final)
    return {'location':str(final),'previous_location':str(source),'source_retained':True,
            'projects':report['projects'],'files':len(before[0])}
