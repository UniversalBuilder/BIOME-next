import unittest, tempfile, json
from synthetic_fixture import create_fixture
from pathlib import Path
from data_store import add_entry, read_project, recover

class FolderTest(unittest.TestCase):
    def setUp(self):
        test_base=Path(__file__).resolve().parent/'test-tmp'
        test_base.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=test_base)
        self.root=Path(self.tmp.name)/'project'
        create_fixture(self.root)
    def tearDown(self): self.tmp.cleanup()
    def test_persistence_and_unknown_time(self):
        before=read_project(self.root)
        entry=add_entry(self.root,{'text':'Test de reprise externe','type':'experiment','date':'2026-10-12','time':'09:37','minutes':45,'tags':'test, paramètres'})
        self.assertEqual(entry['date_source'],'12/10/2026 09:37:00')
        self.assertIn('Test de reprise externe',(self.root/entry['file']).read_text(encoding='utf-8'))
        result=read_project(self.root)
        self.assertEqual(result['total_minutes'],before['total_minutes']+45)
        add_entry(self.root,{'text':'Observation sans durée','type':'note','date':'2026-10-12','minutes':None})
        self.assertEqual(read_project(self.root)['total_minutes'],result['total_minutes'])
        self.assertIn('45',(self.root/'records/activity.csv').read_text(encoding='utf-8-sig'))
        self.assertFalse((self.root/'records/pending-entry.json').exists())
    def test_file_label_correction_preserves_content_and_time(self):
        import base64
        from data_store import make_delivery
        item=add_entry(self.root,{'text':'Script test','type':'experiment','date':'2026-10-14','time':'10:00','minutes':15,'attachments':[{'name':'script.ijm','content':base64.b64encode(b'// macro').decode(),'role':'version','label':'v3','caption':'Old'}]})
        file=item['attachments'][0]
        delivery=make_delivery(self.root,{'files':[file['file']]})
        original=(self.root/delivery['file']).read_bytes()
        current=next(e for e in read_project(self.root)['entries'] if e['id']==item['id'])
        before=read_project(self.root)['total_minutes']
        add_entry(self.root,{'edit_id':item['id'],'base_revision':current['revision'],'text':'Script test','type':'experiment','date':'2026-10-14','time':'10:00','minutes':15,'captions':{file['id']:'Median filtering'},'version_labels':{file['id']:'v3 — median filter'},'attachments':[]})
        updated=next(e for e in read_project(self.root)['entries'] if e['id']==item['id'])['attachments'][0]
        self.assertEqual(updated['version_label'],'v3 — median filter')
        self.assertEqual(updated['caption'],'Median filtering')
        self.assertEqual((self.root/file['file']).read_bytes(),b'// macro')
        self.assertEqual(read_project(self.root)['total_minutes'],before)
        self.assertEqual((self.root/delivery['file']).read_bytes(),original)

    def test_monthly_report_uses_session_dates_and_period(self):
        from data_store import activity_report
        add_entry(self.root,{'text':'Next month','type':'note','date':'2026-11-01','time':'09:00','minutes':25})
        add_entry(self.root,{'text':'Unknown time','type':'note','date':'2026-11-02','time':'09:00','minutes':None})
        add_entry(self.root,{'text':'Future','type':'note','date':'2027-01-01','time':'09:00','minutes':40})
        report=activity_report(self.root,start='2026-10-01',end='2026-11-01')
        self.assertEqual(report['monthly_minutes'],[{'month':'2026-10','minutes':10},{'month':'2026-11','minutes':25}])
        self.assertEqual(sum(item['minutes'] for item in report['monthly_minutes']),report['total_minutes'])
        empty=activity_report(self.root,start='2030-01-01',end='2030-01-02')
        self.assertEqual(empty['monthly_minutes'],[])

    def test_recovery_is_idempotent(self):
        pending={'file':'journal/recovery.md','note':'Note récupérée','entry':{'id':'recovery','date_source':'12/10/2026 12:00:00','type':'note','file':'journal/recovery.md'},'work_log':{'id':'recovery-time','date':'2026-10-12','minutes':12,'activity_type':'note','entry_ids':['recovery'],'description':'Reprise'}}
        path=self.root/'records/pending-entry.json'
        for _ in range(2):
            path.write_text(json.dumps(pending),encoding='utf-8'); recover(self.root)
        result=read_project(self.root)
        self.assertEqual(len([e for e in result['entries'] if e['id']=='recovery']),1)
        self.assertEqual(len([e for e in result['logs'] if e['id']=='recovery-time']),1)
    def test_invalid_input_changes_nothing(self):
        before=(self.root/'records/entries.json').read_bytes()
        with self.assertRaises(ValueError): add_entry(self.root,{'text':'x','type':'note','date':'2026-10-12','minutes':-1})
        self.assertEqual(before,(self.root/'records/entries.json').read_bytes())

if __name__=='__main__': unittest.main()
