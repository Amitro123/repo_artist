import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add scripts directory to path to import smart_push
scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
sys.path.insert(0, scripts_dir)

import smart_push


class TestRunCommand(unittest.TestCase):
    """Tests for run_command function with list-based subprocess calls."""
    
    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        mock_run.return_value = MagicMock(stdout="output", returncode=0)
        result = smart_push.run_command(["git", "status"], check=False)
        self.assertEqual(result, "output")
        mock_run.assert_called_once()
        # Verify shell=True is NOT used
        call_kwargs = mock_run.call_args[1]
        self.assertNotIn('shell', call_kwargs)
    
    @patch('subprocess.run')
    def test_run_command_list_format(self, mock_run):
        """Verify command is passed as list, not string (security fix)."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        smart_push.run_command(["git", "push", "origin", "main"], check=False)
        # First positional arg should be the command list
        call_args = mock_run.call_args[0][0]
        self.assertIsInstance(call_args, list)
        self.assertEqual(call_args, ["git", "push", "origin", "main"])


class TestGetGitChanges(unittest.TestCase):
    """Tests for get_git_changes function."""
    
    @patch('smart_push.run_command')
    def test_parse_git_diff_output(self, mock_run):
        """Test parsing of git diff --shortstat output."""
        def side_effect(cmd, check=True):
            # cmd is now a list, so check if command appears in list
            if "rev-parse" in cmd:
                return "origin/main"
            if "diff" in cmd:
                return " 4 files changed, 60 insertions(+), 10 deletions(-)"
            return ""
        mock_run.side_effect = side_effect
        
        files, lines = smart_push.get_git_changes()
        self.assertEqual(files, 4)
        self.assertEqual(lines, 70)  # 60 insertions + 10 deletions
    
    @patch('smart_push.run_command')
    def test_no_upstream_branch(self, mock_run):
        """Test handling when no upstream branch exists."""
        mock_run.return_value = ""
        files, lines = smart_push.get_git_changes()
        self.assertEqual(files, 0)
        self.assertEqual(lines, 0)


class TestThresholds(unittest.TestCase):
    """Tests for configurable threshold logic."""
    
    def test_default_thresholds(self):
        """Test that default thresholds are set."""
        self.assertEqual(smart_push.FILE_THRESHOLD, 3)
        self.assertEqual(smart_push.LINE_THRESHOLD, 50)
    
    def test_threshold_constants_exist(self):
        """Test that threshold constants can be read from module."""
        self.assertTrue(hasattr(smart_push, 'FILE_THRESHOLD'))
        self.assertTrue(hasattr(smart_push, 'LINE_THRESHOLD'))
        # Thresholds should be positive integers
        self.assertIsInstance(smart_push.FILE_THRESHOLD, int)
        self.assertIsInstance(smart_push.LINE_THRESHOLD, int)
        self.assertGreater(smart_push.FILE_THRESHOLD, 0)
        self.assertGreater(smart_push.LINE_THRESHOLD, 0)


class TestSmartPushIntegration(unittest.TestCase):
    """Integration tests for main() function."""

    @patch('smart_push.run_command')
    @patch('builtins.input')
    @patch('subprocess.call')
    def test_smart_push_trigger(self, mock_call, mock_input, mock_run_command):
        """Test that significant changes trigger art generation prompt."""
        mock_input.side_effect = ['y', '1']
        
        def side_effect(cmd, check=True):
            # cmd is now a list, check if command appears in list
            if "rev-parse" in cmd:
                return "origin/main"
            if "diff" in cmd:
                return " 4 files changed, 60 insertions(+), 0 deletions(-)"
            return ""
            
        mock_run_command.side_effect = side_effect
        mock_call.return_value = 0
        
        with patch('sys.argv', ['smart_push.py']):
            with self.assertRaises(SystemExit) as cm:
                smart_push.main()
        
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(mock_input.call_count, 2)
        
        # Verify commit was called with list format
        commit_called = False
        for call in mock_run_command.call_args_list:
            args = call[0][0] if call[0] else []
            if isinstance(args, list) and "commit" in args:
                commit_called = True
                break
        self.assertTrue(commit_called, "Expected git commit to be called")

    @patch('smart_push.run_command')
    @patch('builtins.input', return_value='n')
    @patch('subprocess.call')
    def test_smart_push_no_trigger_small_change(self, mock_call, mock_input, mock_run_command):
        """Test that small changes don't trigger prompt."""
        def side_effect(cmd, check=True):
            # cmd is now a list
            if "rev-parse" in cmd:
                return "origin/main"
            if "diff" in cmd:
                return " 1 files changed, 10 insertions(+), 0 deletions(-)"
            return ""
            
        mock_run_command.side_effect = side_effect
        mock_call.return_value = 0
        
        with patch('sys.argv', ['smart_push.py']):
            with self.assertRaises(SystemExit) as cm:
                smart_push.main()
        
        # Verify NO prompt for small changes
        self.assertFalse(mock_input.called)


if __name__ == '__main__':
    unittest.main()

