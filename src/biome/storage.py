"""File operations independent of the HTTP interface."""
import json
import os
import uuid
import time
from pathlib import Path

from project_format import validate_project


def publish_directory(source,destination):
    """Publish without replacement; tolerate brief Windows scanner locks only."""
    source=Path(source);destination=Path(destination)
    delays=[0,.05,.1,.2,.4,.8,.8]
    for attempt,delay in enumerate(delays):
        if delay:time.sleep(delay)
        if destination.exists() or destination.is_symlink():raise ValueError('Le dossier de destination existe déjà ; aucun remplacement.')
        try:
            source.rename(destination)
            return destination
        except PermissionError as error:
            if os.name!='nt' or getattr(error,'winerror',None) not in [5,32,33] or not source.is_dir() or attempt==len(delays)-1:
                raise


def load(path):
    path = Path(path)
    value = json.loads(path.read_text(encoding='utf-8'))
    if path.name == 'biome.json':
        validate_project(value)
    return value


def atomic(path, text):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        temp.write_text(text, encoding='utf-8')
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def write_json(path, value):
    path = Path(path)
    if path.name == 'biome.json':
        validate_project(value)
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def safe_file(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Chemin hors du projet')
    return path
