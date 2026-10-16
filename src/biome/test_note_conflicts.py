import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data_store as biome


class ConflictTest(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).resolve().parent/'test-tmp';scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch)
        anchor=Path(self.temp.name)/'.catalog-anchor'
        created=biome.create_project(anchor,{'title':'Synthetic conflict','contact':'Test person','request':'Synthetic request'})
        self.root=biome.project_catalog(anchor)[created['key']]
        self.entry=biome.add_entry(self.root,{'text':'Original note','type':'note','date':'2026-10-14','time':'10:00','minutes':20})
        self.path=self.root/self.entry['file']
        self.draft={'edit_id':self.entry['id'],'base_revision':biome.entry_revision(self.root,self.entry),
                    'text':'Local correction','type':'note','date':'2026-10-14','time':'10:00','minutes':30}

    def tearDown(self): self.temp.cleanup()

    def external_change(self):
        self.path.write_text(self.path.read_text(encoding='utf-8').replace('Original note','External correction'),encoding='utf-8')

    def test_conflict_preserves_note_time_and_both_versions(self):
        self.external_change();current=self.path.read_bytes()
        with self.assertRaises(biome.EntryConflict) as error: biome.add_entry(self.root,self.draft)
        self.assertEqual(self.path.read_bytes(),current)
        self.assertEqual(biome.read_project(self.root)['total_minutes'],20)
        record=biome.load(self.root/error.exception.payload['saved_copy'])
        self.assertEqual(record['draft']['text'],'Local correction')
        self.assertIn('External correction',error.exception.payload['current_note'])
        self.assertFalse((self.root/'records/pending-entry.json').exists())

    def test_explicit_retry_rechecks_and_preserves_history(self):
        self.external_change()
        with self.assertRaises(biome.EntryConflict) as error: biome.add_entry(self.root,self.draft)
        self.draft['base_revision']=error.exception.payload['current_revision']
        external=self.path.read_text(encoding='utf-8')
        biome.add_entry(self.root,self.draft)
        self.assertEqual(biome.read_project(self.root)['total_minutes'],30)
        histories=list((self.root/'records/history').glob('*.json'))
        self.assertTrue(any(biome.load(p)['note']==external for p in histories))
        with self.assertRaises(biome.EntryConflict): biome.add_entry(self.root,self.draft)

    def test_metadata_change_and_missing_revision_blocked(self):
        records=biome.load(self.root/'records/entries.json')
        next(item for item in records if item['id']==self.entry['id'])['tags']=['other-window']
        biome.write_json(self.root/'records/entries.json',records)
        with self.assertRaises(biome.EntryConflict): biome.add_entry(self.root,self.draft)
        self.draft.pop('base_revision')
        with self.assertRaises(biome.EntryConflict): biome.add_entry(self.root,self.draft)

    def test_deleted_file_is_not_recreated(self):
        self.path.unlink()
        with self.assertRaises(biome.EntryConflict) as error: biome.add_entry(self.root,self.draft)
        self.assertTrue(error.exception.payload['missing'])
        self.assertFalse(self.path.exists())

    def test_interrupted_edit_does_not_overwrite_external_text(self):
        with patch('data_store.recover',side_effect=RuntimeError('Interrupted')):
            with self.assertRaises(RuntimeError): biome.add_entry(self.root,self.draft)
        self.external_change();current=self.path.read_bytes()
        with self.assertRaises(biome.EntryConflict): biome.recover(self.root)
        self.assertEqual(self.path.read_bytes(),current)
        self.assertFalse((self.root/'records/pending-entry.json').exists())
        self.assertEqual(biome.read_project(self.root)['total_minutes'],20)

    def test_recovery_accepts_own_partial_write(self):
        with patch('data_store.recover',side_effect=RuntimeError('Interrupted')):
            with self.assertRaises(RuntimeError): biome.add_entry(self.root,self.draft)
        pending=biome.load(self.root/'records/pending-entry.json')
        self.path.write_text(pending['note'],encoding='utf-8')
        biome.recover(self.root)
        self.assertEqual(biome.read_project(self.root)['total_minutes'],30)
        biome.recover(self.root)
        self.assertEqual(biome.read_project(self.root)['total_minutes'],30)

    def test_http_conflict_and_explicit_resolution(self):
        import json,re,subprocess,sys,time,urllib.request,urllib.error
        endpoint='http://127.0.0.1:8767'
        process=subprocess.Popen([sys.executable,str(Path(biome.__file__).with_name('server.py')),'--project',str(self.root),
            '--settings',str(Path(self.temp.name)/'settings.json'),'--port','8767'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000)
        try:
            for _ in range(30):
                try: page=urllib.request.urlopen(endpoint,timeout=2).read().decode();break
                except OSError: time.sleep(.2)
            else: self.fail('Test server unavailable')
            token=re.search("const token='([^']+)'",page).group(1)
            state=json.load(urllib.request.urlopen(endpoint+'/api/project'))
            self.draft['base_revision']=next(e['revision'] for e in state['entries'] if e['id']==self.entry['id'])
            self.external_change()
            def request():
                return urllib.request.urlopen(urllib.request.Request(endpoint+'/api/entries',
                    data=json.dumps(self.draft).encode(),headers={'Content-Type':'application/json','X-Biome-Token':token}))
            with self.assertRaises(urllib.error.HTTPError) as error: request()
            self.assertEqual(error.exception.code,409)
            conflict=json.loads(error.exception.read())
            self.assertTrue(conflict['conflict'])
            self.assertIn('External correction',conflict['current_note'])
            self.draft['base_revision']=conflict['current_revision']
            with request() as response: self.assertEqual(response.status,201)
            self.assertEqual(biome.read_project(self.root)['total_minutes'],30)
        finally:
            process.terminate();process.wait(timeout=5)


if __name__=='__main__': unittest.main()
