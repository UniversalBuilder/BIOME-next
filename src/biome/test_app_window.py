import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app_window import open_window

class AppWindowTest(unittest.TestCase):
    def test_app_window_is_separate_from_personal_profile(self):
        scratch=Path(__file__).resolve().parent/'test-tmp';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp,patch('app_window.find_browser',return_value=Path('C:/Browser/chrome.exe')),patch('app_window.subprocess.Popen') as popen:
            open_window('http://127.0.0.1:8766/',tmp)
            args=popen.call_args.args[0]
            self.assertIn('--app=http://127.0.0.1:8766/',args)
            self.assertIn('--user-data-dir='+str(Path(tmp).resolve()/'Browser'),args)
            self.assertTrue((Path(tmp)/'Browser').is_dir())
            self.assertFalse(any('disable-web-security' in value or 'no-sandbox' in value for value in args))
    def test_non_local_url_rejected_before_launch(self):
        with patch('app_window.subprocess.Popen') as popen:
            with self.assertRaises(ValueError):open_window('https://example.org','unused')
            popen.assert_not_called()
    def test_missing_browser_is_explicit(self):
        with patch('app_window.find_browser',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'Edge'):open_window('http://127.0.0.1:8766/','unused')

if __name__=='__main__':unittest.main()
