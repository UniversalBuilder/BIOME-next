import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from app_window import WindowLifetime,ApplicationWindows


class WindowLifetimeTest(unittest.TestCase):
    def test_startup_is_not_mistaken_for_closed_window(self):
        life=WindowLifetime(100)
        self.assertFalse(life.should_stop(110,0))
        self.assertFalse(life.should_stop(120,1))
        self.assertFalse(life.should_stop(200,1))

    def test_last_window_closure_has_short_grace(self):
        life=WindowLifetime(0)
        life.should_stop(2,1)
        self.assertFalse(life.should_stop(3,0))
        self.assertFalse(life.should_stop(4,0))
        self.assertTrue(life.should_stop(4.6,0))

    def test_other_window_and_temporary_replacement_keep_app_alive(self):
        life=WindowLifetime(0)
        for stamp,count in [(2,2),(3,1),(100,1),(101,0),(102,1),(500,1)]:
            self.assertFalse(life.should_stop(stamp,count))
        self.assertFalse(life.should_stop(501,0))
        self.assertTrue(life.should_stop(503,0))

    def test_startup_failure_does_not_leave_server_forever(self):
        life=WindowLifetime(0)
        self.assertFalse(life.should_stop(44,0))
        self.assertTrue(life.should_stop(45,0))

    def test_only_live_owned_processes_and_unique_session_profile_are_used(self):
        scratch=Path(__file__).parent/'test-tmp';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            first=ApplicationWindows(tmp,'http://127.0.0.1:1234/')
            second=ApplicationWindows(tmp,'http://127.0.0.1:4321/')
            self.assertNotEqual(first.profile,second.profile)
            self.assertEqual(first.profile.parent,Path(tmp)/'Browser')
            browser=MagicMock(pid=123);browser.poll.return_value=None
            launcher=MagicMock(pid=456);launcher.poll.return_value=0
            with patch('app_window.open_window',side_effect=[browser,launcher]) as launch:
                first.open();first.lifetime.seen=True;first.open()
                self.assertFalse(first.lifetime.seen)
                self.assertEqual(launch.call_args.args[2],first.profile)
            with patch('app_window.browser_windows',return_value=[789]) as windows:
                self.assertEqual(first.owned_windows(),[789])
                windows.assert_called_once_with({123})


if __name__=='__main__':unittest.main()
