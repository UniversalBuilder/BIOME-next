import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

import data_store as store
from data_folders import create_data_folder, folder_info, project_data_path, LAYOUT
from data_receipts import preview_receipt, receive_data


class ProjectDataFolderTest(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).parent/'test-tmp';scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch)
        self.base=Path(self.temp.name).resolve();self.catalog=self.base/'catalog';self.catalog.mkdir()
        anchor=self.catalog/'.anchor'
        item=store.create_project(anchor,{'title':'Segmentation des cellules','contact':'Romane Example','group':'Équipe Démo','request':'Synthetic request'})
        self.root=store.project_catalog(anchor)[item['key']]
        self.parent=self.base/'Originals';self.parent.mkdir()
        self.name=folder_info(self.root)['suggested_name']

    def tearDown(self):self.temp.cleanup()
    def create(self):return create_data_folder(self.root,{'parent':str(self.parent),'name':self.name})

    def test_identifiable_layout_reference_and_default_receipt_destination(self):
        self.assertIn('Equipe-Demo_Romane-Example_Segmentation-des-cellules',self.name)
        self.assertEqual(self.name,folder_info(self.root)['suggested_name'])
        record=self.create();folder=self.parent/self.name
        self.assertEqual({p.name for p in folder.iterdir()},set(LAYOUT)|{'README.txt'})
        self.assertIn('Romane Example',(folder/'README.txt').read_text(encoding='utf-8'))
        self.assertIn(store.load(self.root/'biome.json')['id'],(folder/'README.txt').read_text(encoding='utf-8'))
        self.assertEqual(project_data_path(self.root,record['id']),folder)
        data=store.read_project(self.root)
        self.assertEqual(data['data_folder']['default_raw'],str(folder/'01_raw'))
        source=self.base/'image.tif';source.write_bytes(b'synthetic image')
        preview=preview_receipt(str(source))
        received=receive_data(self.root,{**preview,'storage':'external','destination':data['data_folder']['default_raw']})
        self.assertTrue(Path(received['location']).is_relative_to(folder/'01_raw'))
        self.assertEqual((Path(received['location'])/'image.tif').read_bytes(),source.read_bytes())
        self.assertFalse((self.root/'data').exists())

    def test_no_overwrite_and_no_reorganization_of_existing_folder(self):
        folder=self.parent/self.name;folder.mkdir();(folder/'keep.tif').write_bytes(b'original')
        with self.assertRaisesRegex(ValueError,'existe déjà'):self.create()
        self.assertEqual({p.name for p in folder.iterdir()},{'keep.tif'})
        self.assertEqual(store.load(self.root/'records/datasets.json'),[])
        store.add_dataset(self.root,{'name':'Existing originals','role':'original','location':str(folder)})
        self.assertEqual({p.name for p in folder.iterdir()},{'keep.tif'})

    def test_catalogue_overlap_and_invalid_names_are_rejected(self):
        for parent,name in [(self.catalog,'data'),(self.root,'data'),(self.base,'catalog'),(self.parent,'../escape'),(self.parent,'A/B'),(self.parent,'CON'),(self.parent,'NUL.txt'),(self.parent,'name.'),(self.parent,' a'),(self.parent,'a:b')]:
            with self.subTest(parent=parent,name=name):
                with self.assertRaises(ValueError):create_data_folder(self.root,{'parent':str(parent),'name':name})
        self.assertFalse((self.catalog/'data').exists())
        self.assertEqual(store.load(self.root/'records/datasets.json'),[])

    def test_duplicate_submission_keeps_same_folder_and_reference(self):
        record=self.create();(Path(record['location'])/'keep.tif').write_bytes(b'original')
        with self.assertRaisesRegex(ValueError,'déjà un dossier'):self.create()
        self.assertEqual(len(store.load(self.root/'records/datasets.json')),1)
        self.assertEqual((Path(record['location'])/'keep.tif').read_bytes(),b'original')

    def test_failed_registry_write_cleans_only_new_empty_structure(self):
        with patch('data_folders.write_json',side_effect=OSError('test failure')):
            with self.assertRaises(OSError):self.create()
        self.assertFalse((self.parent/self.name).exists())
        self.assertEqual(store.load(self.root/'records/datasets.json'),[])

    def test_editing_reference_clears_old_structured_pointer(self):
        record=self.create();other=self.parent/'Existing';other.mkdir()
        store.add_dataset(self.root,{**record,'edit_id':record['id'],'location':str(other)})
        self.assertIsNone(folder_info(self.root)['structured'])
        self.assertTrue((self.parent/self.name/'README.txt').exists())
        with self.assertRaises(ValueError):project_data_path(self.root,record['id'])

    def test_http_creation_is_authenticated_and_returns_persistent_folder(self):
        state=self.base/'state';state.mkdir()
        command='from pathlib import Path;from server import serve;import sys;serve(Path(sys.argv[1]),0,Path(sys.argv[2]),state_dir=Path(sys.argv[3]))'
        process=subprocess.Popen([sys.executable,'-u','-c',command,str(self.root),str(state/'settings.json'),str(state)],cwd=Path(__file__).parent,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        try:
            url=process.stdout.readline().strip().split()[-1]
            payload=json.dumps({'parent':str(self.parent),'name':self.name}).encode()
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(urllib.request.Request(url+'/api/create-data-folder',data=payload),timeout=10)
            self.assertEqual(error.exception.code,403)
            self.assertFalse((self.parent/self.name).exists())
            token=(state/'.local-session-token').read_text(encoding='utf-8')
            req=urllib.request.Request(url+'/api/create-data-folder',data=payload,headers={'X-Biome-Token':token,'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=10) as response:created=json.load(response)
            self.assertEqual(Path(created['location']),self.parent/self.name/'01_raw')
            with urllib.request.urlopen(url+'/api/project',timeout=10) as response:result=json.load(response)
            self.assertEqual(result['data_folder']['structured']['id'],created['id'])
        finally:
            process.terminate();process.wait(timeout=10);process.stdout.close()


if __name__=='__main__':unittest.main()
