import base64
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import data_store as biome
from backups import create_backup, restore_backup


class BackupTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent / 'test-tmp'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'catalog'
        self.target = self.base / 'backups'
        self.restore = self.base / 'restore'
        for path in [self.source, self.target, self.restore]:
            path.mkdir()
        created = biome.create_project(self.source / '.catalog-anchor', {
            'title': 'Synthetic backup', 'contact': 'Test person', 'group': 'Test lab',
            'request': 'Synthetic original request'})
        self.project = biome.project_catalog(self.source / '.catalog-anchor')[created['key']]
        self.note = biome.add_entry(self.project, {'text': 'Synthetic session', 'type': 'experiment',
            'date': '2026-10-14', 'time': '14:20', 'minutes': 40,
            'attachments': [{'name': 'pilot.py', 'content': base64.b64encode(b'pass\n').decode()}]})
        biome.add_dataset(self.project, {'name': 'NAS reference', 'role': 'original',
                                        'location': r'\\synthetic-server\share\images'})
        biome.vocabularies(self.source / '.catalog-anchor')
        (self.project / 'manual-file.txt').write_text('Manually added document', encoding='utf-8')
        (self.project / 'empty-folder').mkdir()
        (self.source / '.local-session-token').write_text('Excluded local setting', encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self, root):
        return {p.relative_to(root).as_posix():
                (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in root.rglob('*') if p.is_file()}

    def backup(self):
        return Path(create_backup(self.source, str(self.target))['file'])

    def test_restore_preserves_identity_files_times_and_source(self):
        before = self.snapshot(self.source)
        archive = self.backup()
        first = restore_backup(str(archive), str(self.restore))
        second = restore_backup(str(archive), str(self.restore))
        self.assertNotEqual(first['location'], second['location'])
        restored = Path(first['location']) / self.project.name
        original = biome.read_project(self.project)
        current = biome.read_project(restored)
        self.assertEqual(original['project'], current['project'])
        self.assertEqual(current['total_minutes'], 40)
        self.assertEqual(current['entries'], original['entries'])
        self.assertTrue((restored / 'empty-folder').is_dir())
        self.assertEqual((restored / 'manual-file.txt').read_text(), 'Manually added document')
        self.assertFalse((Path(first['location']) / '.local-session-token').exists())
        self.assertEqual(self.snapshot(self.source), before)
        with zipfile.ZipFile(archive) as packed:
            manifest = json.loads(packed.read('backup-manifest.json'))
            self.assertFalse(manifest['external_data_included'])
            self.assertEqual(manifest['external_references'], 1)

    def test_destination_inside_source_and_pending_rejected(self):
        with self.assertRaises(ValueError):
            create_backup(self.source, str(self.project))
        pending = self.project / 'records/pending-info.json'
        pending.write_text('{}', encoding='utf-8')
        before = self.snapshot(self.source)
        with self.assertRaises(ValueError):
            self.backup()
        self.assertEqual(self.snapshot(self.source), before)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_corrupt_content_does_not_publish_or_overwrite(self):
        archive = self.backup()
        broken = self.target / 'altered.zip'
        with zipfile.ZipFile(archive) as original, zipfile.ZipFile(broken, 'w') as output:
            for name in original.namelist():
                data = original.read(name)
                if name.endswith('pilot.py'):
                    data = b'fail\n'  # Same length, valid ZIP CRC, incorrect SHA-256.
                output.writestr(name, data)
        marker = self.restore / 'existing.txt'
        marker.write_text('Preserve existing data', encoding='utf-8')
        with self.assertRaises(ValueError):
            restore_backup(str(broken), str(self.restore))
        self.assertEqual(list(self.restore.iterdir()), [marker])
        self.assertEqual(marker.read_text(), 'Preserve existing data')

    def test_traversal_archive_is_rejected(self):
        archive = self.target / 'unsafe.zip'
        manifest = {'format': 'biome-documentary-backup', 'version': 1, 'directories': [],
                    'files': {'../escape.txt': {'bytes': 1, 'sha256': '0' * 64}}}
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('backup-manifest.json', json.dumps(manifest))
            output.writestr('README.txt', '')
            output.writestr('catalog/../escape.txt', 'x')
        with self.assertRaises(ValueError):
            restore_backup(str(archive), str(self.restore))
        self.assertEqual(list(self.restore.iterdir()), [])
        self.assertFalse((self.base / 'escape.txt').exists())

    def test_source_changed_during_copy_is_not_published(self):
        import backups
        real = backups.inventory
        calls = 0
        def changed(root):
            nonlocal calls
            calls += 1
            value = real(root)
            if calls > 1:
                value[0]['new-file.txt'] = (1, 1)
            return value
        with patch('backups.inventory', side_effect=changed):
            with self.assertRaises(ValueError):
                self.backup()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_http_actions_preserve_current_catalogue(self):
        import re
        import subprocess
        import sys
        import time
        import urllib.request
        import urllib.error
        endpoint = 'http://127.0.0.1:8767'
        process = subprocess.Popen([sys.executable, str(Path(biome.__file__).with_name('server.py')), '--project',
            str(self.source / '.catalog-anchor'), '--settings', str(self.base / 'settings.json'),
            '--port', '8767'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=0x08000000)
        try:
            for _ in range(30):
                try:
                    page = urllib.request.urlopen(endpoint, timeout=2).read().decode()
                    break
                except OSError:
                    time.sleep(.2)
            else:
                self.fail('Test server unavailable')
            token = re.search("const token='([^']+)'", page).group(1)
            def post(route, body, authenticated=True):
                headers = {'Content-Type': 'application/json'}
                if authenticated:
                    headers['X-Biome-Token'] = token
                return json.load(urllib.request.urlopen(urllib.request.Request(
                    endpoint + route, data=json.dumps(body).encode(), headers=headers), timeout=15))
            with self.assertRaises(urllib.error.HTTPError) as error:
                post('/api/backup', {'destination': str(self.target)}, False)
            self.assertEqual(error.exception.code, 403)
            saved = post('/api/backup', {'destination': str(self.target)})
            restored = post('/api/restore', {'archive': saved['file'], 'destination': str(self.restore)})
            self.assertTrue(Path(restored['location']).is_dir())
            workspace = json.load(urllib.request.urlopen(endpoint + '/api/workspace'))
            self.assertEqual(Path(workspace['location']), self.source)
            # These routes must not execute the normal automatic recovery hook.
            (self.project / 'records/pending-info.json').write_text('{}', encoding='utf-8')
            before = self.snapshot(self.source)
            with self.assertRaises(urllib.error.HTTPError) as error:
                post('/api/backup', {'destination': str(self.target)})
            self.assertEqual(error.exception.code, 400)
            self.assertEqual(self.snapshot(self.source), before)
        finally:
            process.terminate()
            process.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
