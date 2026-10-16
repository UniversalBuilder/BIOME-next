import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data_store as biome
from diagnostics import diagnose_catalog, check_external


class DiagnosticTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent / 'test-tmp'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.catalog = Path(self.temp.name)
        created = biome.create_project(self.catalog / '.catalog-anchor', {
            'title': 'Synthetic project', 'contact': 'Test contact', 'group': 'Test group',
            'request': 'Synthetic request'})
        self.root = biome.project_catalog(self.catalog / '.catalog-anchor')[created['key']]
        self.entry = biome.add_entry(self.root, {'text': 'Synthetic test', 'type': 'experiment',
            'date': '2026-10-14', 'time': '11:00', 'minutes': 25,
            'attachments': [{'name': 'test.py', 'content': base64.b64encode(b'pass\n').decode()}]})

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self):
        return {p.relative_to(self.catalog).as_posix():
                (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in self.catalog.rglob('*') if p.is_file()}

    def test_healthy_and_no_external_probe(self):
        biome.add_dataset(self.root, {'name': 'NAS', 'role': 'original',
                                      'location': r'\\not-a-real-server\share\images'})
        before = self.snapshot()
        original = Path.is_file

        def guarded(path):
            self.assertNotIn('not-a-real-server', str(path))
            return original(path)

        with patch.object(Path, 'is_file', guarded):
            result = diagnose_catalog(self.catalog)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(result['warnings'], 0)
        self.assertEqual(result['external_references'], 1)
        self.assertEqual(self.snapshot(), before)

    def test_multiple_failures_are_reported_without_recovery(self):
        (self.root / self.entry['attachments'][0]['file']).unlink()
        logs = biome.load(self.root / 'records/work-logs.json')
        logs['logs'][0]['minutes'] = -5
        logs['logs'][0]['entry_ids'] = ['unknown']
        biome.write_json(self.root / 'records/work-logs.json', logs)
        (self.root / 'records/pending-info.json').write_text('{}', encoding='utf-8')
        broken = self.catalog / 'broken-project'
        broken.mkdir()
        (broken / 'biome.json').write_text('{invalid', encoding='utf-8')
        before = self.snapshot()
        result = diagnose_catalog(self.catalog)
        self.assertEqual(result['projects'], 2)
        self.assertGreaterEqual(result['errors'], 4)
        self.assertEqual(result['warnings'], 1)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_shapes_and_escape_links(self):
        biome.write_json(self.catalog / '.biome-directory.json', {'contacts': 'invalid', 'groups': [{'id': []}]})
        biome.write_json(self.root / 'records/versions.json', [{'id': 'escape', 'file': '../outside.txt'}])
        biome.write_json(self.root / 'records/entries.json', [None, {'id': 'bad', 'file': 'x.md', 'date_source': None}])
        result = diagnose_catalog(self.catalog)
        self.assertGreaterEqual(result['errors'], 5)
        self.assertTrue(any('sortant' in item['message'] for item in result['findings']))

    def test_external_access_present_missing_and_timeout(self):
        present = self.catalog / 'external.txt'
        present.write_text('synthetic', encoding='utf-8')
        item = {'project': 'test', 'name': 'external', 'location': str(present.resolve())}
        self.assertEqual(check_external(item)['state'], 'accessible')
        self.assertEqual(check_external({**item, 'location': str(self.catalog / 'missing')})['state'], 'missing')
        import subprocess
        with patch('diagnostics.subprocess.run', side_effect=subprocess.TimeoutExpired('probe', 3)):
            self.assertEqual(check_external(item)['state'], 'timeout')
        before = self.snapshot()
        biome.add_dataset(self.root, {'name': 'external', 'role': 'original', 'location': str(present.resolve())})
        before = self.snapshot()
        report = diagnose_catalog(self.catalog, check_locations=True)
        self.assertEqual(report['locations'][0]['state'], 'accessible')
        self.assertEqual(self.snapshot(), before)

    def test_probe_with_windows_legacy_encoding_and_unicode_path(self):
        present = self.catalog / 'échantillon-細胞.txt'
        present.write_text('synthetic', encoding='utf-8')
        environment = {**os.environ, 'PYTHONIOENCODING': 'cp1252', 'PYTHONUTF8': '0'}
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name('check_location.py'))],
            input=json.dumps({'location': str(present.resolve())}).encode('ascii'),
            capture_output=True, env=environment, check=True)
        result.stdout.decode('ascii')
        self.assertEqual(json.loads(result.stdout)['detail'], 'Fichier présent et lisible')
        item = {'project': 'test', 'name': 'unicode', 'location': str(present.resolve())}
        with patch.dict(os.environ, environment):
            self.assertEqual(check_external(item)['state'], 'accessible')
        with patch('diagnostics.subprocess.run', return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=b'{invalid}', stderr=b'\xe9')):
            self.assertEqual(check_external(item)['state'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
