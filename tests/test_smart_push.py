import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import smart_push
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import smart_push

class TestSmartPush(unittest.TestCase):

    @patch('smart_push.run_command')
    @patch('builtins.input')
    @patch('subprocess.call')
    def test_smart_push_trigger(self, mock_call, mock_input, mock_run_command):
        # Setup mocks
        # Mock the two-step input: first 'y' for generate, then '1' for full refresh
        mock_input.side_effect = ['y', '1']
        
        # partial side effect for run_command to handle different calls
        def side_effect(cmd, check=True):
            if "git rev-parse" in cmd:
                return "origin/main"
            if "git diff" in cmd:
                # Simulate big change
                return " 4 files changed, 60 insertions(+), 0 deletions(-)"
            return ""
            
        mock_run_command.side_effect = side_effect
        
        # Mock subprocess.call to return 0 (success)
        mock_call.return_value = 0
        
        # Run main
        with patch('sys.argv', ['smart_push.py']):
            with self.assertRaises(SystemExit) as cm:
                smart_push.main()
        
        # Verify exit code is 0
        self.assertEqual(cm.exception.code, 0)
        
        # Verify both prompts were called
        self.assertEqual(mock_input.call_count, 2)
        
        # Check if commit was called
        commit_called = False
        for call in mock_run_command.call_args_list:
            if "git commit" in str(call):
                commit_called = True
                break
        self.assertTrue(commit_called, "Expected git commit to be called")

    @patch('smart_push.run_command')
    @patch('builtins.input', return_value='n')
    @patch('subprocess.call')
    def test_smart_push_no_trigger_small_change(self, mock_call, mock_input, mock_run_command):
        # Setup mocks
        def side_effect(cmd):
            if "git rev-parse" in cmd:
                return "origin/main"
            if "git diff" in cmd:
                # Simulate small change
                return " 1 files changed, 10 insertions(+), 0 deletions(-)"
            return ""
            
        mock_run_command.side_effect = side_effect
        
        # Run main
        with patch('sys.argv', ['smart_push.py']):
            with self.assertRaises(SystemExit) as cm:
                smart_push.main()
        
        # Verify NO prompt
        self.assertFalse(mock_input.called)

if __name__ == '__main__':
    unittest.main()
