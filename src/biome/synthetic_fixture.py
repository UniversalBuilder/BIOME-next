"""Small, reproducible test project. Never reads a user's catalogue."""
from pathlib import Path
import base64
import data_store as store
from storage import publish_directory


def create_fixture(destination):
    destination=Path(destination).resolve()
    if destination.exists(): raise ValueError('Fixture destination must be new')
    destination.parent.mkdir(parents=True,exist_ok=True)
    anchor=destination.parent/'.catalog-anchor'
    created=store.create_project(anchor,{'title':'Synthetic fixture','contact':'Alex Example','group':'Example Lab','request':'Fictional test request. No personal or scientific data.'})
    generated=store.project_catalog(anchor)[created['key']]
    publish_directory(generated,destination)
    store.add_entry(destination,{'type':'experiment','text':'Synthetic baseline session','date':'2026-10-12','time':'09:00','minutes':10,'attachments':[{'name':'baseline.ijm','content':base64.b64encode(b'// synthetic fixture\n').decode(),'role':'version','label':'v1'}]})
    return destination
