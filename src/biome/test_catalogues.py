import json
import tempfile
import unittest
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

import data_store as store
from catalogues import create_catalogue,open_catalogue,remember_catalogue
from demo_catalogue import install_demo
from diagnostics import diagnose_catalog


class CatalogueTest(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).parent/'test-tmp';scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch);self.base=Path(self.temp.name).resolve()
    def tearDown(self):self.temp.cleanup()

    def test_create_and_recognize_empty_catalogue_without_overwriting(self):
        info=create_catalogue(str(self.base),'My catalogue')
        self.assertEqual(open_catalogue(info['location'])['id'],info['id'])
        self.assertEqual(info['projects'],0)
        with self.assertRaises(ValueError):create_catalogue(str(self.base),'My catalogue')
        arbitrary=self.base/'not-a-catalogue';arbitrary.mkdir()
        with self.assertRaises(ValueError):open_catalogue(str(arbitrary))
        for invalid in ['../escape','CON','bad:name','a/b']:
            with self.assertRaises(ValueError):create_catalogue(str(self.base),invalid)

    def test_originals_link_is_separate_and_source_is_untouched(self):
        info=create_catalogue(str(self.base),'Catalogue');catalogue=Path(info['location'])
        originals=self.base/'Originals';originals.mkdir();image=originals/'sample.png';image.write_bytes(b'Original remains unchanged')
        item=store.create_project(catalogue/'.catalog-anchor',{'title':'Example','contact':'Test person','request':'Request','originals_location':str(originals)})
        root=store.project_catalog(catalogue/'.catalog-anchor')[item['key']]
        dataset=store.load(root/'records/datasets.json')[0]
        self.assertEqual(dataset['location'],str(originals));self.assertEqual(dataset['storage'],'external')
        self.assertEqual(image.read_bytes(),b'Original remains unchanged')
        self.assertFalse((root/'data').exists())
        before=list(catalogue.iterdir())
        for invalid in [catalogue,self.base,root]:
            with self.assertRaises(ValueError):store.create_project(catalogue/'.catalog-anchor',{'title':'Invalid','contact':'Test','request':'Request','originals_location':str(invalid)})
        self.assertEqual(set(before),set(catalogue.iterdir()))

    def test_remember_preserves_preferences_and_recent_catalogues(self):
        settings=self.base/'settings.json';settings.write_text(json.dumps({'language':'fr','location':'previous'}))
        remember_catalogue(settings,'new');remember_catalogue(settings,'new')
        value=json.loads(settings.read_text());self.assertEqual(value['language'],'fr')
        self.assertEqual(value['recent_catalogues'],['new','previous'])

    def test_demo_uses_only_generated_data_and_can_be_installed_independently(self):
        result=install_demo(str(self.base));catalogue=Path(result['location'])
        self.assertTrue(result['demo']);self.assertEqual(result['projects'],3)
        projects=store.project_catalog(catalogue/'.catalog-anchor')
        self.assertEqual(len(projects),3)
        for root in projects.values():
            data=store.read_project(root);self.assertTrue(data['project']['demo'])
            self.assertTrue(data['project']['contact_email'].endswith('@example.org'))
            for dataset in data['datasets']:
                location=Path(dataset['location'])
                self.assertTrue(location.is_dir());self.assertFalse(location.is_relative_to(catalogue))
                self.assertNotIn('.installing-demo-',dataset['location'])
            for delivery in data['deliveries']:self.assertTrue((root/delivery['file']).is_file())
        self.assertEqual(diagnose_catalog(catalogue)['errors'],0)
        with self.assertRaises(ValueError):install_demo(str(self.base))
        another=self.base/'another';another.mkdir()
        second=install_demo(str(another));self.assertEqual(second['projects'],3)

    def test_first_launch_create_demo_and_reopen_previous_catalogue(self):
        empty=self.base/'empty';empty.mkdir();state=self.base/'state';state.mkdir();settings=state/'workspace.json'
        command='from pathlib import Path;from server import serve;import sys;serve(Path(sys.argv[1]),0,Path(sys.argv[2]),state_dir=Path(sys.argv[3]),catalogue_required=True)'
        process=subprocess.Popen([sys.executable,'-u','-c',command,str(empty/'.catalog-anchor'),str(settings),str(state)],cwd=Path(__file__).parent,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        try:
            url=process.stdout.readline().strip().split()[-1];token=(state/'.local-session-token').read_text().strip()
            def get(route):
                with urllib.request.urlopen(url+route,timeout=10) as response:return json.load(response)
            def post(route,data):
                request=urllib.request.Request(url+route,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Biome-Token':token},method='POST')
                with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
            self.assertTrue(get('/api/workspace')['needs_selection'])
            with self.assertRaises(urllib.error.HTTPError):post('/api/projects',{'title':'Not yet','contact':'Test','request':'Request'})
            created=post('/api/catalogue-create',{'destination':str(self.base),'name':'Personal catalogue'})
            self.assertFalse(get('/api/workspace')['needs_selection'])
            demo=post('/api/demo-install',{'destination':str(self.base)})
            self.assertEqual(len(get('/api/projects')),3)
            self.assertTrue(get('/api/workspace')['demo'])
            self.assertIn(created['location'],get('/api/workspace')['recent_catalogues'])
            post('/api/catalogue-open',{'location':created['location']})
            self.assertEqual(get('/api/projects'),[])
            self.assertFalse(get('/api/workspace').get('demo'))
            with self.assertRaises(urllib.error.HTTPError):post('/api/catalogue-open',{'location':str(self.base)})
            self.assertEqual(get('/api/workspace')['location'],created['location'])
        finally:
            process.terminate();process.wait(timeout=10)
            if process.stdout:process.stdout.close()


if __name__=='__main__':unittest.main()
