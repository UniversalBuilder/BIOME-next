import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import data_store as store


class DirectoryRemovalTests(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).parent/'test-tmp';scratch.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.initial=Path(self.tmp.name)/'.catalog-anchor'
        self.project=store.create_project(self.initial,{'title':'Example','contact':'Old contact','group':'Old lab','email':'old@example.org','request':'Original request'})
        self.root=store.project_catalog(self.initial)[self.project['key']]

    def item(self,kind,name):
        return next(x for x in store.directory(self.initial)[kind] if x['name']==name)

    def payload(self,kind,name,replacement=None):
        data={'kind':kind,'id':self.item(kind,name)['id']}
        if replacement:data['replacement_id']=self.item(kind,replacement)['id']
        data['revision']=store.directory_removal_preview(self.initial,data)['revision']
        return data

    def test_unused_deletion_and_used_requires_replacement(self):
        store.add_directory_item(self.initial,{'kind':'groups','name':'Unused'})
        store.remove_directory_item(self.initial,self.payload('groups','Unused'))
        self.assertNotIn('Unused',[x['name'] for x in store.directory(self.initial)['groups']])
        with self.assertRaisesRegex(ValueError,'remplacement'):
            store.remove_directory_item(self.initial,self.payload('contacts','Old contact'))
        with self.assertRaises(ValueError):
            self.payload('groups','Old lab','Old lab')

    def test_merge_updates_email_and_preserves_history_and_notes(self):
        store.add_directory_item(self.initial,{'kind':'contacts','name':'New contact','email':'new@example.org'})
        before={p.relative_to(self.root):p.read_bytes() for p in (self.root/'journal').glob('*') if p.is_file()}
        store.remove_directory_item(self.initial,self.payload('contacts','Old contact','New contact'))
        project=store.load(self.root/'biome.json')
        self.assertEqual(project['contact'],'New contact')
        self.assertEqual(project['contact_email'],'new@example.org')
        self.assertEqual(project['contact_id'],self.item('contacts','New contact')['id'])
        self.assertNotIn('Old contact',[x['name'] for x in store.directory(self.initial)['contacts']])
        histories=[store.load(p) for p in (self.root/'records/project-history').glob('*.json')]
        self.assertTrue(any(h['previous']['contact']=='Old contact' for h in histories))
        for relative,raw in before.items():self.assertEqual((self.root/relative).read_bytes(),raw)

    def test_stale_preview_rejected_without_mutation(self):
        store.add_directory_item(self.initial,{'kind':'groups','name':'New lab'})
        data=self.payload('groups','Old lab','New lab')
        store.create_project(self.initial,{'title':'Another','contact':'Other','group':'Old lab','request':'Request'})
        with self.assertRaisesRegex(ValueError,'changé'):store.remove_directory_item(self.initial,data)
        self.assertEqual(store.load(self.root/'biome.json')['group'],'Old lab')

    def test_legacy_name_matching_and_interrupted_operation_recovery(self):
        project=store.load(self.root/'biome.json');project.pop('group_id',None);store.write_json(self.root/'biome.json',project)
        store.add_directory_item(self.initial,{'kind':'groups','name':'New lab'})
        data=self.payload('groups','Old lab','New lab')
        with patch('data_store.update_project_info',side_effect=OSError('Interrupted')):
            with self.assertRaises(OSError):store.remove_directory_item(self.initial,data)
        store.recover_directory(self.initial);store.recover_directory(self.initial)
        self.assertEqual(store.load(self.root/'biome.json')['group'],'New lab')
        self.assertNotIn('Old lab',[x['name'] for x in store.directory(self.initial)['groups']])
        self.assertEqual(len(store.directory(self.initial)['history']),1)


if __name__=='__main__':unittest.main()
