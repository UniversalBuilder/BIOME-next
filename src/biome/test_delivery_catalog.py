import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from unittest.mock import patch
import zipfile

import data_store as store
from delivery_catalog import inventory, preview, image_bytes
from delivery_catalog import readable_title, note_body
from demo_catalogue import synthetic_png
from synthetic_fixture import create_fixture


class DeliveryCatalogTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).parent / 'test-tmp'; scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'project'; create_fixture(self.root)
        image = self.base / 'sample.png'; synthetic_png(image)
        self.image = image.read_bytes()
        self.entry = store.add_entry(self.root, {'type': 'exchange', 'date': '2026-10-19', 'time': '10:00',
            'text': 'Objet : Essais de segmentation\nDe : Fictional person\n\nSynthetic recommendation.',
            'attachments': [
                {'name': 'image001.png', 'content': base64.b64encode(self.image).decode(), 'caption': 'Comparaison des résultats'},
                {'name': 'macro_v2.ijm', 'content': base64.b64encode(b'// test macro').decode(), 'role': 'version', 'label': 'v2', 'caption': 'Median filter added'},
                {'name': 'original.msg', 'content': base64.b64encode(b'fake-message').decode(), 'caption': 'Message source importé'}]})

    def tearDown(self):
        self.temp.cleanup()

    def test_readable_inventory_keeps_origin_and_technical_sources_distinct(self):
        legacy = self.root / 'files/legacy-source'; legacy.mkdir()
        (legacy / 'biome.json').write_text('{}')
        files = inventory(self.root)
        group = [item for item in files if item['group'] == self.entry['id']]
        self.assertEqual(len(group), 4)
        self.assertTrue(all(item['group_title'] == 'Essais de segmentation' for item in group))
        image = next(item for item in group if item['kind'] == 'image')
        self.assertEqual(image['title'], 'Comparaison des résultats')
        self.assertEqual(image['name'], 'image001.png')
        macro = next(item for item in group if item['kind'] == 'script')
        self.assertEqual(macro['version'], 'v2')
        self.assertFalse(macro['technical'])
        self.assertTrue(next(item for item in group if item['kind'] == 'source')['technical'])
        self.assertTrue(next(item for item in files if item['file'] == 'files/legacy-source/biome.json')['technical'])

    def test_windows_markdown_headers_are_not_display_titles(self):
        text = '---\r\nid: synthetic\r\n---\r\n\r\nMedian filter recommendations\r\n\r\nSome details.'
        self.assertEqual(readable_title(text, 'Note'), 'Median filter recommendations')
        self.assertNotIn('id: synthetic', note_body(text))

    def test_safe_bounded_previews_and_original_download_bytes(self):
        image = self.entry['attachments'][0]['file']
        self.assertEqual(image_bytes(self.root, image), (self.image, 'image/png'))
        self.assertEqual(preview(self.root, image)['mode'], 'image')
        macro = self.entry['attachments'][1]['file']
        self.assertEqual(preview(self.root, macro)['text'], '// test macro')
        long = self.root / 'files/long.txt'; long.write_text('x' * 70_000)
        bounded = preview(self.root, 'files/long.txt')
        self.assertTrue(bounded['truncated']); self.assertEqual(len(bounded['text']), 64_000)
        with self.assertRaises(ValueError): preview(self.root, '../outside.txt')
        with self.assertRaises(ValueError): preview(self.root, 'biome.json')
        with self.assertRaises(ValueError): image_bytes(self.root, macro)

    def test_outlook_preview_does_not_extract_attachments(self):
        message = {'headers': [('Objet', 'Synthetic message')], 'body': 'Text only', 'html': '', 'date': None}
        with patch('mail_messages.read_msg', return_value=message) as reader:
            result = preview(self.root, self.entry['attachments'][2]['file'])
        reader.assert_called_once_with(b'fake-message', include_images=False)
        self.assertIn('Text only', result['text'])
        self.assertIn('original complet', result['notice'])

    def test_delivery_freezes_labels_and_only_explicitly_selected_files(self):
        chosen = [item for item in inventory(self.root) if item['group'] == self.entry['id'] and item['kind'] in ['image', 'script']]
        source_bytes = {(self.root / item['file']): (self.root / item['file']).read_bytes() for item in chosen}
        label = '<script>alert("example")</script>'
        result = store.make_delivery(self.root, {'files': [item['file'] for item in chosen],
            'display_labels': {chosen[0]['file']: label},
            'revisions': {item['file']: item['revision'] for item in chosen}, 'note': 'Recipient instructions'})
        with zipfile.ZipFile(self.root / result['file']) as archive:
            self.assertEqual(set(archive.namelist()), {item['file'] for item in chosen} | {'README.html', 'README.md', 'manifest.json'})
            page = archive.read('README.html').decode()
            self.assertIn('&lt;script&gt;', page); self.assertNotIn(label, page)
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['selection'][0]['title'], label)
            for item in chosen:
                self.assertEqual(archive.read(item['file']), source_bytes[self.root / item['file']])
        frozen = (self.root / result['file']).read_bytes()
        (self.root / chosen[0]['file']).write_bytes(b'changed later')
        self.assertEqual((self.root / result['file']).read_bytes(), frozen)

    def test_changed_selection_is_rejected_before_creating_archive(self):
        item = next(item for item in inventory(self.root) if item['kind'] == 'script')
        before = store.load(self.root / 'records/deliveries.json') if (self.root / 'records/deliveries.json').exists() else []
        (self.root / item['file']).write_bytes(b'new script version')
        with self.assertRaisesRegex(ValueError, 'changé'):
            store.make_delivery(self.root, {'files': [item['file']], 'revisions': {item['file']: item['revision']}})
        after = store.load(self.root / 'records/deliveries.json') if (self.root / 'records/deliveries.json').exists() else []
        self.assertEqual(after, before)

    def test_preview_routes_and_assets_in_real_http_adapter(self):
        state = self.base / 'state'; state.mkdir()
        command = 'from pathlib import Path;from server import serve;import sys;serve(Path(sys.argv[1]),0,Path(sys.argv[2]),state_dir=Path(sys.argv[3]))'
        process = subprocess.Popen([sys.executable, '-u', '-c', command, str(self.root), str(state / 'settings.json'), str(state)],
            cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            url = process.stdout.readline().strip().split()[-1]
            for path in ['/delivery-selector.js', '/delivery-selector.css']:
                with urllib.request.urlopen(url + path) as response: self.assertEqual(response.status, 200)
            from urllib.parse import quote
            file = self.entry['attachments'][0]['file']
            with urllib.request.urlopen(url + '/api/delivery-preview?file=' + quote(file)) as response:
                self.assertEqual(json.load(response)['mode'], 'image')
            with urllib.request.urlopen(url + '/api/delivery-preview?image=1&file=' + quote(file)) as response:
                self.assertEqual(response.headers['Content-Type'], 'image/png')
                self.assertEqual(response.read(), self.image)
            with urllib.request.urlopen(url + '/api/delivery-preview?download=1&file=' + quote(file)) as response:
                self.assertIn('attachment', response.headers['Content-Disposition'])
                self.assertEqual(response.read(), self.image)
        finally:
            process.terminate(); process.wait(timeout=10); process.stdout.close()


if __name__ == '__main__': unittest.main()
