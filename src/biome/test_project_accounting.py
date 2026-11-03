import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import data_store as store
from project_accounting import AccountingConflict, save_accounting, revision
from synthetic_fixture import create_fixture


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.scratch=Path(__file__).resolve().parent/'test-tmp';self.scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=self.scratch)
        self.root=create_fixture(Path(self.temp.name)/'project')

    def tearDown(self):
        self.temp.cleanup()

    def save(self, action='save', **values):
        work=store.load(self.root/'records/work-logs.json')
        return save_accounting(self.root, {'action':action,'base_revision':revision(work),'date':'2026-05-14','minutes':90,**values})

    def clear_times(self):
        store.write_json(self.root/'records/work-logs.json',{'logs':[]})

    def test_manual_crud_is_dated_and_does_not_create_or_change_notes(self):
        notes={p.name:p.read_bytes() for p in (self.root/'journal').iterdir()}
        entries=(self.root/'records/entries.json').read_bytes()
        added=self.save();manual=next(log for log in added['logs'] if log.get('source')=='manual')
        self.assertEqual(added['total_minutes'],100)
        self.assertEqual(manual['entry_ids'],[])
        self.assertEqual(store.activity_report(self.root,2026)['total_minutes'],100)
        self.assertEqual(store.activity_report(self.root,start='2026-05-01',end='2026-05-31')['total_minutes'],90)
        self.save(id=manual['id'],minutes=120,date='2025-03-08')
        self.assertEqual(store.activity_report(self.root,2026)['total_minutes'],10)
        self.assertEqual(store.activity_report(self.root,2025)['total_minutes'],120)
        self.save(action='delete',id=manual['id'])
        self.assertEqual(store.read_project(self.root)['total_minutes'],10)
        work=store.load(self.root/'records/work-logs.json')
        self.assertEqual(work['accounting_history'][-1]['previous']['minutes'],120)
        self.assertEqual(entries,(self.root/'records/entries.json').read_bytes())
        self.assertEqual(notes,{p.name:p.read_bytes() for p in (self.root/'journal').iterdir()})

    def test_absent_time_and_explicit_zero_are_different(self):
        self.clear_times()
        project=store.read_project(self.root)
        self.assertFalse(project['time_recorded'])
        report=store.activity_report(self.root,2026)
        self.assertIsNone(report['projects'][0]['minutes'])
        self.assertEqual(report['projects_with_time'],0)
        self.assertIsNone(report['average_minutes'])
        self.assertEqual(report['monthly_minutes'],[])
        self.save(minutes=0)
        report=store.activity_report(self.root,2026)
        self.assertTrue(store.read_project(self.root)['time_recorded'])
        self.assertEqual(report['projects_with_time'],1)
        self.assertEqual(report['explicit_zero_projects'],1)
        self.assertEqual(report['average_minutes'],0)
        self.assertEqual(report['monthly_minutes'],[{'month':'2026-05','minutes':0}])

    def test_exclusion_is_reversible_and_applies_to_every_chart_period_and_export(self):
        self.save(minutes=6000,estimate=True)
        before=store.read_project(self.root)['logs']
        self.save(action='scope',excluded=True,reason='Internal development, not representative')
        report=store.activity_report(self.root,2026)
        self.assertEqual(report['projects'],[])
        self.assertEqual(report['total_minutes'],0)
        self.assertEqual(report['group_count'],0)
        self.assertEqual(report['monthly_minutes'],[])
        self.assertEqual(len(report['excluded_projects']),1)
        self.assertTrue(all(not value['items'] for value in report['breakdowns'].values()))
        self.assertEqual(store.activity_report(self.root,start='2026-05-01',end='2026-05-31')['total_minutes'],0)
        self.assertEqual(store.read_project(self.root)['logs'],before)
        with zipfile.ZipFile(io.BytesIO(store.export_activity(report))) as archive:
            rows=lambda name:list(csv.reader(io.StringIO(archive.read(name).decode('utf-8-sig'))))
            self.assertEqual(len(rows('projects.csv')),1)
            self.assertEqual(len(rows('excluded-projects.csv')),2)
            self.assertIn('not representative',rows('excluded-projects.csv')[1][3])
            self.assertEqual(json.loads(archive.read('activity-report.json'))['total_minutes'],0)
            self.assertNotIn('0 h 0 min renseignées',archive.read('README.html').decode())
            self.assertTrue(archive.read('activity-report.pdf').startswith(b'%PDF'))
        self.save(action='scope',excluded=False,reason='')
        self.assertEqual(store.activity_report(self.root,2026)['total_minutes'],6010)

    def test_missing_metadata_excludes_only_the_relevant_statistic(self):
        project=store.load(self.root/'biome.json')
        project.update(group='[Non Renseigné]',contact='Unknown')
        project['framing']={'software':['Fiji'],'activity_type':'analysis','modalities':[],'topics':[]}
        store.write_json(self.root/'biome.json',project)
        report=store.activity_report(self.root,2026)
        self.assertEqual(report['total_minutes'],10)
        self.assertEqual(report['group_count'],0)
        self.assertEqual(report['contact_count'],0)
        self.assertEqual(report['breakdowns']['group']['items'],[])
        self.assertEqual(report['breakdowns']['software']['included'],1)
        self.assertEqual(report['breakdowns']['activity_type']['included'],1)
        self.assertEqual(report['breakdowns']['group']['missing_category'],1)
        self.clear_times();report=store.activity_report(self.root,2026)
        self.assertEqual(report['breakdowns']['activity_type']['missing_time'],1)
        self.assertEqual(report['breakdowns']['software']['included'],1)

    def test_bad_dates_durations_and_linked_log_changes_do_not_write(self):
        previous=(self.root/'records/work-logs.json').read_bytes()
        linked=store.read_project(self.root)['logs'][0]['id']
        for values in [{'date':'2026-02-30'},{'date':'2026-5-1'},{'minutes':None},{'minutes':True},{'minutes':-1},{'minutes':1441},{'minutes':525601,'estimate':True},{'estimate':'yes'},{'id':linked},{'action':'delete','id':linked}]:
            with self.subTest(values=values),self.assertRaises(ValueError):self.save(**values)
            self.assertEqual(previous,(self.root/'records/work-logs.json').read_bytes())
        estimate=self.save(minutes=6000,estimate=True)
        self.assertEqual(estimate['estimated_minutes'],6000)
        from diagnostics import diagnose_catalog
        self.assertEqual(diagnose_catalog(self.root.parent)['errors'],0)

    def test_stale_revision_cannot_overwrite_a_time_or_scope_change(self):
        stale=store.read_project(self.root)['work_revision']
        self.save()
        previous=(self.root/'records/work-logs.json').read_bytes()
        with self.assertRaises(AccountingConflict):
            save_accounting(self.root,{'action':'scope','base_revision':stale,'excluded':True,'reason':''})
        self.assertEqual(previous,(self.root/'records/work-logs.json').read_bytes())

    def test_interrupted_csv_write_recovers_without_duplicate_time(self):
        stale=store.read_project(self.root)['work_revision']
        with patch('project_accounting.write_csv',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):self.save()
        self.assertTrue((self.root/'records/pending-accounting.json').exists())
        project=store.read_project(self.root)
        self.assertEqual(project['total_minutes'],100)
        self.assertEqual(len(project['logs']),2)
        self.assertFalse((self.root/'records/pending-accounting.json').exists())
        self.assertEqual(len(store.load(self.root/'records/work-logs.json')['accounting_history']),1)
        with self.assertRaises(AccountingConflict):
            save_accounting(self.root,{'action':'save','base_revision':stale,'date':'2026-05-14','minutes':90})
        with (self.root/'records/activity.csv').open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(sum(int(row['minutes']) for row in rows),100)

    def test_note_edit_preserves_standalone_times_scope_and_history(self):
        self.save(minutes=45)
        self.save(action='scope',excluded=True,reason='Test scope')
        entry=next(e for e in store.read_project(self.root)['entries'] if e['type']=='experiment')
        store.add_entry(self.root,{'edit_id':entry['id'],'base_revision':entry['revision'],'type':'experiment','date':'2026-10-12','time':'09:00','text':'Corrected baseline','minutes':20,'tags':'','attachments':[]})
        project=store.read_project(self.root)
        self.assertEqual(project['total_minutes'],65)
        self.assertTrue(project['reporting']['excluded'])
        self.assertEqual(project['manual_minutes'],45)
        self.assertEqual(len(store.load(self.root/'records/work-logs.json')['accounting_history']),2)

    def test_backup_restores_scope_and_independent_estimates(self):
        from backups import create_backup,restore_backup
        self.save(minutes=6000,estimate=True)
        self.save(action='scope',excluded=True,reason='Atypical')
        target=Path(self.temp.name)/'Backups';target.mkdir()
        # The backup destination must be outside the source catalogue.
        with tempfile.TemporaryDirectory(dir=self.scratch) as other:
            destination=Path(other);archive=create_backup(self.root.parent,str(destination))['file']
            restored=restore_backup(archive,str(destination))
            project=next(iter(store.project_catalog(Path(restored['location'])/'.catalog-anchor').values()))
            result=store.read_project(project)
            self.assertEqual(result['estimated_minutes'],6000)
            self.assertTrue(result['reporting']['excluded'])


    def test_average_uses_only_known_time_and_respects_project_scope(self):
        unknown=create_fixture(Path(self.temp.name)/'unknown')
        zero=create_fixture(Path(self.temp.name)/'zero')
        store.write_json(unknown/'records/work-logs.json',{'logs':[]})
        zero_work=store.load(zero/'records/work-logs.json');zero_work['logs'][0]['minutes']=0;store.write_json(zero/'records/work-logs.json',zero_work)
        report=store.activity_report(self.root,2026)
        self.assertEqual(len(report['projects']),3)
        self.assertEqual(report['projects_with_time'],2)
        self.assertEqual(report['projects_without_time'],1)
        self.assertEqual(report['average_minutes'],5)
        self.save(action='scope',excluded=True,reason='Out of population')
        report=store.activity_report(self.root,2026)
        self.assertEqual(report['average_minutes'],0)
        self.assertEqual(report['projects_with_time'],1)

    def test_http_authentication_stale_writes_and_project_isolation(self):
        import socket,subprocess,sys,time,urllib.request,urllib.error
        sibling=create_fixture(Path(self.temp.name)/'second')
        with socket.socket() as socket_handle:
            socket_handle.bind(('127.0.0.1',0));port=socket_handle.getsockname()[1]
        process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py')),'--project',str(self.root),'--settings',str(Path(self.temp.name)/'settings.json'),'--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000)
        base='http://127.0.0.1:'+str(port)
        try:
            for _ in range(60):
                try:
                    with urllib.request.urlopen(base+'/',timeout=1) as response:page=response.read().decode();break
                except OSError:time.sleep(.1)
            else:self.fail('Test server unavailable')
            import re
            token=re.search("const token='([^']+)'",page).group(1)
            key=next(key for key,path in store.project_catalog(self.root).items() if path==sibling)
            query='?project='+key
            def get(route):
                with urllib.request.urlopen(base+route,timeout=10) as response:return json.load(response)
            def post(payload,authenticated=True):
                headers={'Content-Type':'application/json'}
                if authenticated:headers['X-Biome-Token']=token
                req=urllib.request.Request(base+'/api/accounting'+query,data=json.dumps(payload).encode(),headers=headers)
                with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
            state=get('/api/project'+query)
            payload={'action':'save','base_revision':state['work_revision'],'date':'2026-04-05','minutes':45}
            with self.assertRaises(urllib.error.HTTPError) as context:post(payload,False)
            self.assertEqual(context.exception.code,403)
            state=post(payload)
            self.assertEqual(state['total_minutes'],55)
            self.assertEqual(store.read_project(self.root)['total_minutes'],10)
            with self.assertRaises(urllib.error.HTTPError) as context:post(payload)
            self.assertEqual(context.exception.code,409)
            post({'action':'scope','base_revision':state['work_revision'],'excluded':True,'reason':'Not representative'})
            report=get('/api/activity-report?year=2026')
            self.assertEqual(report['total_minutes'],10)
            self.assertEqual(len(report['excluded_projects']),1)
            with urllib.request.urlopen(base+'/accounting.js',timeout=10) as response:
                self.assertTrue(response.headers['Content-Type'].startswith('application/javascript'))
        finally:
            process.terminate();process.wait(timeout=10)


if __name__=='__main__':unittest.main()
