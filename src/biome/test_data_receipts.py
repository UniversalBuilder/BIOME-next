import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data_store as biome
from backups import create_backup, restore_backup
from data_receipts import preview_receipt, receive_data, dataset_path, recover_receipt
from diagnostics import diagnose_catalog


class ReceiptTest(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).resolve().parent/'test-tmp';scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch)
        self.base=Path(self.temp.name).resolve();self.catalog=self.base/'catalog';self.catalog.mkdir()
        anchor=self.catalog/'.catalog-anchor'
        created=biome.create_project(anchor,{'title':'Reception test','contact':'Test person','request':'Test images'})
        self.root=biome.project_catalog(anchor)[created['key']]
        self.source=self.base/'download';self.source.mkdir()
        (self.source/'nested').mkdir()
        (self.source/'nested/small.tif').write_bytes(b'Synthetic data')
        (self.source/'large.bin').write_bytes(b'x'*(6*1024*1024))
        self.destination=self.base/'durable';self.destination.mkdir()

    def tearDown(self): self.temp.cleanup()

    def payload(self,storage='project'):
        preview=preview_receipt(str(self.source))
        return {'source':preview['source'],'signature':preview['signature'],'storage':storage,
                'destination':str(self.destination),'name':'Received examples','provenance':'Temporary transfer'}

    def test_folder_large_files_portability_and_backup(self):
        before={p.relative_to(self.source):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.source.rglob('*') if p.is_file()}
        record=receive_data(self.root,self.payload())
        self.assertEqual(record['file_count'],2)
        self.assertFalse(Path(record['location']).is_absolute())
        manifest=biome.load(self.root/record['receipt'])
        for item in manifest['files']:
            original=self.source/item['file'];copied=dataset_path(self.root,record)/item['file']
            self.assertEqual(original.read_bytes(),copied.read_bytes())
            self.assertEqual(hashlib.sha256(copied.read_bytes()).hexdigest(),item['sha256'])
        self.assertEqual(before,{p.relative_to(self.source):(p.read_bytes(),p.stat().st_mtime_ns) for p in self.source.rglob('*') if p.is_file()})
        self.assertEqual(diagnose_catalog(self.catalog)['errors'],0)
        self.assertEqual(diagnose_catalog(self.catalog)['external_references'],0)
        saved=create_backup(self.catalog,str(self.destination))
        result=restore_backup(saved['file'],str(self.destination))
        restored=Path(result['location'])/self.root.name
        self.source.rename(self.base/'expired-source')
        self.assertTrue((dataset_path(restored,record)/'large.bin').is_file())
        self.assertEqual(diagnose_catalog(Path(result['location']))['errors'],0)

    def test_external_copy_and_delivery(self):
        record=receive_data(self.root,self.payload('external'))
        self.assertTrue(Path(record['location']).is_absolute())
        self.assertTrue((dataset_path(self.root,record)/'nested/small.tif').is_file())
        self.assertEqual(diagnose_catalog(self.catalog)['external_references'],1)
        delivery=biome.make_delivery(self.root,{'files':[],'dataset_ids':[record['id']], 'copy_dataset_ids':[record['id']]})
        self.assertTrue((self.root/delivery['file']).is_file())

    def test_changed_selection_and_recursive_destination_rejected(self):
        payload=self.payload();(self.source/'new.txt').write_text('Changed',encoding='utf-8')
        with self.assertRaises(ValueError): receive_data(self.root,payload)
        recursive=self.source/'destination';recursive.mkdir()
        payload=self.payload('external');payload['destination']=str(recursive)
        with self.assertRaises(ValueError): receive_data(self.root,payload)
        self.assertEqual(biome.load(self.root/'records/datasets.json'),[])

    def test_verification_failure_never_publishes(self):
        with patch('data_receipts.verify_files',side_effect=ValueError('Invalid copy')):
            with self.assertRaises(ValueError): receive_data(self.root,self.payload())
        self.assertEqual(biome.load(self.root/'records/datasets.json'),[])
        self.assertEqual(list((self.root/'data/original').iterdir()),[])
        self.assertTrue((self.source/'large.bin').is_file())

    def test_interrupted_publication_is_recoverable_once(self):
        with patch('data_receipts.recover_receipt',side_effect=RuntimeError('Interrupted')):
            with self.assertRaises(RuntimeError): receive_data(self.root,self.payload())
        self.assertTrue((self.root/'records/pending-receipt.json').exists())
        recover_receipt(self.root);recover_receipt(self.root)
        self.assertEqual(len(biome.load(self.root/'records/datasets.json')),1)
        self.assertFalse((self.root/'records/pending-receipt.json').exists())

    def test_single_file_and_new_receipt_never_overwrite(self):
        preview=preview_receipt(str(self.source/'large.bin'))
        payload={'source':preview['source'],'signature':preview['signature'],'storage':'project'}
        first=receive_data(self.root,payload);second=receive_data(self.root,payload)
        self.assertNotEqual(first['location'],second['location'])
        self.assertTrue((dataset_path(self.root,first)/'large.bin').is_file())

    def test_http_receive_preview_copy_and_portable_view(self):
        import json,re,subprocess,sys,time,urllib.request,urllib.error
        endpoint='http://127.0.0.1:8767'
        process=subprocess.Popen([sys.executable,str(Path(biome.__file__).with_name('server.py')),
            '--project',str(self.root),'--settings',str(self.base/'settings.json'),'--port','8767'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000)
        try:
            for _ in range(30):
                try:page=urllib.request.urlopen(endpoint,timeout=2).read().decode();break
                except OSError:time.sleep(.2)
            else:self.fail('Test server unavailable')
            token=re.search("const token='([^']+)'",page).group(1)
            def post(route,payload,authenticated=True):
                headers={'Content-Type':'application/json'}
                if authenticated:headers['X-Biome-Token']=token
                return json.load(urllib.request.urlopen(urllib.request.Request(endpoint+route,
                    data=json.dumps(payload).encode(),headers=headers),timeout=20))
            with self.assertRaises(urllib.error.HTTPError) as error:
                post('/api/receive-data',self.payload(),False)
            self.assertEqual(error.exception.code,403)
            preview=post('/api/receive-preview',{'source':str(self.source)})
            record=post('/api/receive-data',{'source':preview['source'],'signature':preview['signature'],'storage':'project'})
            state=json.load(urllib.request.urlopen(endpoint+'/api/project'))
            self.assertEqual(state['datasets'][0]['id'],record['id'])
            self.assertTrue(Path(state['datasets'][0]['resolved_location']).is_dir())
            self.assertFalse(Path(record['location']).is_absolute())
            result=post('/api/datasets',{'edit_id':record['id'],'name':'Renamed examples','role':'original',
                                         'location':record['location'],'description':'Updated note'})
            self.assertEqual(result['storage'],'project')
            receipt_record=biome.load(self.root/'records/datasets.json')[0]
            self.assertEqual(receipt_record['receipt'],record['receipt'])
            with self.assertRaises(urllib.error.HTTPError) as error:
                post('/api/datasets',{'edit_id':record['id'],'name':'No relocation','role':'original',
                                     'location':'changed','description':''})
            self.assertEqual(error.exception.code,400)
        finally:
            process.terminate();process.wait(timeout=5)


if __name__=='__main__': unittest.main()
