import json
import tempfile
import unittest
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

import data_store as store
from catalogue_management import trash_project,trash_contents,restore_project,relocate_catalogue
from diagnostics import diagnose_catalog
from synthetic_fixture import create_fixture


class CatalogueManagementTest(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).parent/'test-tmp';scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch);self.base=Path(self.temp.name)
        self.catalogue=self.base/'catalogue';self.catalogue.mkdir();self.project=create_fixture(self.catalogue/'project')
    def tearDown(self):self.temp.cleanup()

    def test_removal_is_recoverable_and_external_data_untouched(self):
        external=self.base/'original.tif';external.write_bytes(b'untouched original')
        store.add_dataset(self.project,{'name':'Original','role':'original','location':str(external)})
        before={p.relative_to(self.project):p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        item=trash_project(self.catalogue,self.project)
        self.assertEqual(len(store.project_catalog(self.catalogue/'.catalog-anchor')),0)
        self.assertEqual(diagnose_catalog(self.catalogue)['projects'],0)
        self.assertEqual(trash_contents(self.catalogue)[0]['id'],item['id'])
        restore_project(self.catalogue,item['id'])
        self.assertEqual(before,{p.relative_to(self.project):p.read_bytes() for p in self.project.rglob('*') if p.is_file()})
        self.assertEqual(external.read_bytes(),b'untouched original')
        self.assertEqual(trash_contents(self.catalogue),[])

    def test_restore_refuses_overwrite_and_wrong_project_is_rejected(self):
        with self.assertRaises(ValueError):trash_project(self.base,self.project)
        item=trash_project(self.catalogue,self.project);self.project.mkdir()
        with self.assertRaises(ValueError):restore_project(self.catalogue,item['id'])
        self.assertEqual(len(trash_contents(self.catalogue)),1)

    def test_relocation_verifies_owned_data_and_trash_and_retains_source(self):
        item=trash_project(self.catalogue,self.project)
        parent=self.base/'new-storage';parent.mkdir()
        result=relocate_catalogue(self.catalogue,str(parent));new=Path(result['location'])
        self.assertTrue(self.catalogue.exists());self.assertTrue(result['source_retained'])
        self.assertEqual(trash_contents(new)[0]['id'],item['id'])
        restore_project(new,item['id'])
        self.assertEqual(len(store.project_catalog(new/'.catalog-anchor')),1)
        self.assertEqual(len(trash_contents(self.catalogue)),1)
        with self.assertRaises(ValueError):relocate_catalogue(self.catalogue,str(parent))
        with self.assertRaises(ValueError):relocate_catalogue(self.catalogue,str(self.catalogue))

    def test_failed_copy_is_not_published(self):
        parent=self.base/'new-storage';parent.mkdir()
        with patch('catalogue_management.file_hash',side_effect=['one','different']):
            with self.assertRaises(ValueError):relocate_catalogue(self.catalogue,str(parent))
        self.assertFalse((parent/self.catalogue.name).exists())
        self.assertTrue(self.project.exists())

    def test_all_external_locations_checked_with_progress(self):
        records=[{'id':str(i),'name':str(i),'role':'reference','location':str(self.base/f'data-{i}')} for i in range(46)]
        store.write_json(self.project/'records/datasets.json',records)
        progress=[]
        with patch('diagnostics.check_external',side_effect=lambda item:{**item,'state':'accessible','detail':'Present'}) as probe:
            result=diagnose_catalog(self.catalogue,check_locations=True,progress=lambda checked,total:progress.append((checked,total)))
        self.assertEqual(probe.call_count,46);self.assertEqual(len(result['locations']),46)
        self.assertEqual(progress[-1],(46,46));self.assertEqual(result['warnings'],0)

    def test_http_authentication_diagnostic_job_trash_restore_and_relocation(self):
        state=self.base/'state';state.mkdir();settings=state/'workspace.json'
        command='from pathlib import Path;from server import serve;import sys;serve(Path(sys.argv[1]),0,Path(sys.argv[2]),state_dir=Path(sys.argv[3]))'
        process=subprocess.Popen([sys.executable,'-u','-c',command,str(self.project),str(settings),str(state)],
                                 cwd=Path(__file__).parent,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        try:
            url=process.stdout.readline().strip().split()[-1]
            token=(state/'.local-session-token').read_text().strip()
            def get(route):
                with urllib.request.urlopen(url+route,timeout=10) as response:return json.load(response)
            def post(route,value,authorized=True):
                headers={'Content-Type':'application/json'}
                if authorized:headers['X-Biome-Token']=token
                request=urllib.request.Request(url+route,data=json.dumps(value).encode(),headers=headers,method='POST')
                with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)
            key=get('/api/projects')[0]['key']
            with self.assertRaises(urllib.error.HTTPError) as denied:post('/api/project-trash?project='+key,{},False)
            self.assertEqual(denied.exception.code,403)
            job=post('/api/diagnostics-start',{})
            for _ in range(50):
                job=get('/api/diagnostics-progress?id='+job['id'])
                if job['state']!='running':break
                time.sleep(.05)
            self.assertEqual(job['state'],'done');self.assertEqual(job['result']['projects'],1)
            removed=post('/api/project-trash?project='+key,{})
            self.assertEqual(get('/api/projects'),[])
            self.assertEqual(get('/api/trash')[0]['id'],removed['id'])
            post('/api/project-restore',{'id':removed['id']});self.assertEqual(len(get('/api/projects')),1)
            parent=self.base/'destination';parent.mkdir()
            result=post('/api/relocate-catalogue',{'destination':str(parent)})
            self.assertEqual(get('/api/workspace')['location'],result['location'])
            self.assertEqual(json.loads(settings.read_text())['location'],result['location'])
            self.assertTrue(self.project.exists());self.assertEqual(len(get('/api/projects')),1)
        finally:
            process.terminate();process.wait(timeout=10)
            if process.stdout:process.stdout.close()


if __name__=='__main__':unittest.main()
