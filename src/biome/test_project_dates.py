import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.request
import urllib.error
import zipfile
import data_store as store
from project_dates import date_metadata,checked_date_fields
from data_folders import folder_info


class ProjectDatesTest(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).parent/'test-tmp';scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch);self.base=Path(self.temp.name).resolve()
        self.catalog=self.base/'catalog';self.catalog.mkdir();self.anchor=self.catalog/'.anchor'
        created=store.create_project(self.anchor,{'title':'2020.03.24_Emilia-Example','contact':'Example person','request':'Fictional request'})
        self.key=created['key'];self.root=store.project_catalog(self.anchor)[self.key]
        self.technical_date=store.load(self.root/'biome.json')['created_at']

    def tearDown(self):self.temp.cleanup()
    def legacy(self):
        value=store.load(self.root/'biome.json')
        value.update(contact='',group='',legacy_import={'source':str(self.base/'2020.03.24_Emilia-Example'),'source_created_at':None,'source_last_updated':None})
        store.write_json(self.root/'biome.json',value);store.write_json(self.root/'records/entries.json',[])
        return value
    def save(self,**dates):
        p=store.load(self.root/'biome.json')
        return store.update_project_info(self.root,{'title':p['title'],'contact':p['contact'],'group':p.get('group',''),'contact_email':'',**dates})

    def test_suggested_folder_date_requires_confirmation_and_import_date_is_not_used(self):
        value=self.legacy();dates=date_metadata(self.root,value)
        self.assertIsNone(dates['project_date']);self.assertEqual(dates['suggested_project_date'],'2020-03-24')
        self.assertIsNone(store.project_overview(self.root,self.key)['created_at'])
        self.assertNotIn('project_date',store.load(self.root/'biome.json'))

    def test_missing_contact_does_not_block_dates_and_originals_are_preserved(self):
        original=self.legacy();folder=self.root.name
        saved=self.save(project_date='2020-03-24',known_activity_date='2020-04-01')
        self.assertEqual(saved['created_at'],self.technical_date)
        self.assertEqual(saved['legacy_import'],original['legacy_import'])
        overview=store.project_overview(self.root,self.key)
        self.assertEqual(overview['created_at'],'2020-03-24');self.assertTrue(overview['last_activity'].startswith('2020-04-01'))
        self.assertEqual(self.root.name,folder)
        self.assertTrue(folder_info(self.root)['suggested_name'].startswith('2020-03-24_'))
        history=list((self.root/'records/project-history').glob('*.json'))
        self.assertEqual(len(history),1)
        self.assertNotIn('project_date',store.load(history[0])['previous'])
        self.assertIn('Project date: 2020-03-24',(self.root/'records/project-info.md').read_text(encoding='utf-8'))

    def test_explicit_unknown_dates_do_not_fall_back_to_imported_dates(self):
        value=self.legacy();value['legacy_import'].update(source_created_at='2020-03-24',source_last_updated='2020-04-01')
        store.write_json(self.root/'biome.json',value)
        self.save(project_date='',known_activity_date=None)
        overview=store.project_overview(self.root,self.key)
        self.assertIsNone(overview['created_at']);self.assertIsNone(overview['last_activity'])

    def test_real_session_date_remains_authoritative_and_report_is_unchanged(self):
        self.legacy()
        store.add_entry(self.root,{'type':'note','text':'Fictional actual work','date':'2021-05-06','time':'10:00','minutes':20})
        before=store.activity_report(self.anchor,year=2021)
        self.save(project_date='2020-03-24',known_activity_date='2020-04-01')
        self.assertTrue(store.project_overview(self.root,self.key)['last_activity'].startswith('2021-05-06'))
        self.assertEqual(store.activity_report(self.anchor,year=2021),before)
        self.assertEqual(store.activity_report(self.anchor,year=2020)['projects'],[])

    def test_new_projects_are_editable_and_omitted_dates_are_preserved(self):
        self.save(project_date='2019-01-03',known_activity_date='2019-02-04')
        self.save()
        value=store.load(self.root/'biome.json')
        self.assertEqual(value['project_date'],'2019-01-03');self.assertEqual(value['known_activity_date'],'2019-02-04')
        self.assertEqual(value['created_at'],self.technical_date)

    def test_invalid_dates_are_rejected_before_writing(self):
        for value in ['2020-02-30','2021-02-29','24/03/2020','2020-3-24','2020-03-24T12:00:00',True,123,{}]:
            with self.subTest(value=value):
                before=(self.root/'biome.json').read_bytes()
                with self.assertRaises(ValueError):self.save(project_date=value)
                self.assertEqual((self.root/'biome.json').read_bytes(),before)
        self.assertEqual(checked_date_fields({'project_date':'2020-02-29'}),{'project_date':'2020-02-29'})

    def test_information_correction_does_not_create_activity(self):
        self.legacy();self.save(project_date='2020-03-24')
        self.assertIsNone(store.project_overview(self.root,self.key)['last_activity'])
        self.assertEqual(store.activity_report(self.anchor,year=2020)['projects'],[])

    def test_future_deliveries_freeze_the_confirmed_project_date(self):
        self.save(project_date='2020-03-24')
        selected=store.delivery_files(self.root)[0]['file']
        delivery=store.make_delivery(self.root,{'files':[selected]})
        frozen=(self.root/delivery['file']).read_bytes()
        with zipfile.ZipFile(self.root/delivery['file']) as archive:
            self.assertEqual(json.loads(archive.read('manifest.json'))['project_snapshot']['dates']['project_date'],'2020-03-24')
        self.save(project_date='2020-03-25')
        self.assertEqual((self.root/delivery['file']).read_bytes(),frozen)

    def test_http_accepts_unknown_contact_and_rejects_invalid_dates_before_directory_changes(self):
        self.legacy();state=self.base/'state';state.mkdir()
        command='from pathlib import Path;from server import serve;import sys;serve(Path(sys.argv[1]),0,Path(sys.argv[2]),state_dir=Path(sys.argv[3]))'
        process=subprocess.Popen([sys.executable,'-u','-c',command,str(self.root),str(state/'settings.json'),str(state)],cwd=Path(__file__).parent,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        try:
            url=process.stdout.readline().strip().split()[-1]
            token=(state/'.local-session-token').read_text(encoding='utf-8')
            def post(data):
                return urllib.request.urlopen(urllib.request.Request(url+'/api/project-info',data=json.dumps(data).encode(),headers={'X-Biome-Token':token,'Content-Type':'application/json'}),timeout=10)
            path=self.catalog/'.biome-directory.json';before=path.read_bytes()
            payload={'title':'Historical project','contact':'','group':'','contact_email':'','project_date':'2020-03-24','known_activity_date':''}
            with self.assertRaises(urllib.error.HTTPError) as error:post({**payload,'contact':'Do not create this contact','project_date':'2020-02-30'})
            self.assertEqual(error.exception.code,400);self.assertEqual(path.read_bytes(),before)
            with post(payload) as response:result=json.load(response)
            self.assertEqual(result['project_date'],'2020-03-24');self.assertEqual(result['contact'],'')
            with urllib.request.urlopen(url+'/api/projects') as response:overview=json.load(response)[0]
            self.assertEqual(overview['created_at'],'2020-03-24');self.assertIsNone(overview['last_activity'])
        finally:process.terminate();process.wait(timeout=10);process.stdout.close()


if __name__=='__main__':unittest.main()
