import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from storage import publish_directory


class DirectoryPublicationTest(unittest.TestCase):
    def test_brief_scanner_lock_retries_without_overwriting(self):
        scratch=Path(__file__).parent/'test-tmp';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            source=Path(temp)/'pending';source.mkdir();(source/'note.txt').write_text('Preserve')
            target=Path(temp)/'published';real_rename=Path.rename;calls=[]
            error=PermissionError('Temporary scanner lock');error.winerror=32
            def rename(path,destination):
                calls.append(path)
                if len(calls)==1:raise error
                return real_rename(path,destination)
            with patch('storage.Path.rename',rename),patch('storage.time.sleep'):
                publish_directory(source,target)
            self.assertEqual((target/'note.txt').read_text(),'Preserve');self.assertEqual(len(calls),2)
            other=Path(temp)/'other';other.mkdir()
            with self.assertRaises(ValueError):publish_directory(other,target)
            self.assertTrue(other.exists());self.assertEqual((target/'note.txt').read_text(),'Preserve')


if __name__=='__main__':unittest.main()
