import json
import tempfile
import unittest
from pathlib import Path

import data_store as biome
from project_format import validate_project


class ProjectFormatTest(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).resolve().parent/'test-tmp';scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch)
        anchor=Path(self.temp.name)/'.catalog-anchor'
        item=biome.create_project(anchor,{'title':'Stable format','contact':'Test person','request':'Test request'})
        self.root=biome.project_catalog(anchor)[item['key']]
        self.file=self.root/'biome.json'

    def tearDown(self): self.temp.cleanup()

    def test_new_project_uses_v1_without_server(self):
        self.assertEqual(biome.load(self.file)['format_version'],'1.1')
        self.assertEqual(biome.read_project(self.root)['total_minutes'],0)
        import sys
        self.assertNotIn('server',sys.modules)

    def test_draft_remains_unchanged_on_read(self):
        metadata=biome.load(self.file);metadata['format_version']='0.1-draft'
        self.file.write_text(json.dumps(metadata),encoding='utf-8')
        before=self.file.read_bytes()
        biome.read_project(self.root)
        self.assertEqual(self.file.read_bytes(),before)

    def test_unknown_version_refuses_writes_without_mutation(self):
        metadata=biome.load(self.file);metadata['format_version']='2.0'
        self.file.write_text(json.dumps(metadata),encoding='utf-8')
        before={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError):
            biome.add_entry(self.root,{'text':'Do not write','type':'note','date':'2026-10-14','minutes':10})
        self.assertEqual(before,{p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_invalid_core_fields_are_rejected(self):
        metadata=biome.load(self.file)
        for fields in [{'format_version':[]},{'id':''},{'created_at':'2026-10-14T12:00:00'},
                       {'status':{'value':'Invalid'}},{'framing':{'software':'Fiji'}}]:
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                validate_project({**metadata,**fields})

    def test_unrelated_metadata_are_preserved(self):
        metadata=biome.load(self.file);metadata['additional_context']={'free':'Preserve this'}
        biome.write_json(self.file,metadata)
        biome.update_project_info(self.root,{'title':'Corrected title','contact':'Test person',
                                             'group':'','contact_email':''})
        self.assertEqual(biome.load(self.file)['additional_context'],{'free':'Preserve this'})


if __name__=='__main__': unittest.main()
