from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

import data_store as store


class NotebookGuideTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent / 'test-tmp'
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        anchor = Path(temp.name) / '.catalog-anchor'
        project = store.create_project(anchor, {
            'title': 'Synthetic project', 'contact': 'Example', 'request': 'Fictional request',
        })
        self.root = store.project_catalog(anchor)[project['key']]

    def test_quick_step_updates_the_same_framing_and_rejects_stale_editor(self):
        old = store.update_framing(self.root, {
            'status': 'Active', 'objective': 'Compare samples', 'next_step': 'Collect images',
            'software': ['ImageJ'],
        })
        updated = store.update_next_step(self.root, {
            'base_next_step': 'Collect images', 'next_step': 'Segment images',
        })
        self.assertEqual(updated['framing'], {**old['framing'], 'next_step': 'Segment images'})
        self.assertEqual(updated['status'], old['status'])
        with self.assertRaisesRegex(ValueError, 'a changé'):
            store.update_framing(self.root, {'status': 'Review', 'base_next_step': 'Collect images'})
        self.assertEqual(store.read_project(self.root)['project'], updated)

    def test_pinned_note_retry_and_stale_delete(self):
        self.assertEqual(store.read_project(self.root)['pinned_notes'], [])
        payload = {'id': str(uuid4()), 'text': 'Check reference image'}
        first = store.save_pinned_note(self.root, payload)
        self.assertEqual(store.save_pinned_note(self.root, payload), first)
        updated = store.save_pinned_note(self.root, {
            **payload, 'text': 'Check second channel', 'revision': first[0]['revision'],
        })
        with self.assertRaisesRegex(ValueError, 'a changé'):
            store.save_pinned_note(self.root, {**first[0], 'remove': True})
        self.assertEqual(store.read_project(self.root)['pinned_notes'], updated)
        self.assertEqual(store.save_pinned_note(self.root, {**updated[0], 'remove': True}), [])

    def test_formatted_body_and_zero_duration_survive_metadata_edit(self):
        payload = {'text': '**Test**\n\n- A\n- B', 'type': 'note', 'date': '2026-11-01', 'minutes': 0}
        created = store.add_entry(self.root, {**payload, 'body_format': 'markdown'})
        edit = {**payload, 'edit_id': created['id'], 'base_revision': store.entry_revision(self.root, created)}
        store.add_entry(self.root, edit)
        project = store.read_project(self.root)
        note = next(entry for entry in project['entries'] if entry['id'] == created['id'])
        self.assertEqual(note['body_format'], 'markdown')
        self.assertEqual(note['text'], payload['text'])
        self.assertTrue(project['time_recorded'])
        self.assertEqual(project['total_minutes'], 0)
        self.assertTrue(any('body_format' not in entry for entry in project['entries']))

    def test_rich_note_preserves_formatting_and_rejects_active_markup(self):
        payload = {'type': 'note', 'date': '2026-11-01', 'body_format': 'rich'}
        text = '<p><strong>Plan</strong></p><ol start="2"><li>Comparer</li></ol>'
        created = store.add_entry(self.root, {**payload, 'text': text})
        note = next(entry for entry in store.read_project(self.root)['entries'] if entry['id'] == created['id'])
        self.assertEqual(note['text'], text)
        self.assertEqual(note['body_format'], 'rich')
        for invalid in ['<img src="remote">', '<p onclick="alert(1)">Plan</p>']:
            with self.assertRaisesRegex(ValueError, 'Mise en forme'):
                store.add_entry(self.root, {**payload, 'text': invalid})
