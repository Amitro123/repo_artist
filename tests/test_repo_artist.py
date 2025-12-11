import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

import repo_artist

class TestRepoArtist(unittest.TestCase):

    @patch('repo_artist.genai')
    @patch('repo_artist.replicate')
    @patch('repo_artist.save_image')
    @patch('os.walk')
    @patch('builtins.open', new_callable=mock_open, read_data="print('hello')")
    def test_full_flow(self, mock_file, mock_walk, mock_save, mock_replicate, mock_genai):
        # Mock Harvesting
        mock_walk.return_value = [
            ('.', [], ['test.py'])
        ]
        
        # Mock Gemini
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = "A flowing data stream."
        mock_model.generate_content.return_value = mock_response
        
        # Mock Replicate
        mock_replicate.run.return_value = ["http://example.com/image.png"]
        
        # Set fake API keys
        repo_artist.GEMINI_API_KEY = "fake_key"
        repo_artist.REPLICATE_API_TOKEN = "fake_token"
        
        # Run
        repo_artist.main()
        
        # Verify Gemini called
        mock_model.generate_content.assert_called()
        
        # Verify Replicate called
        mock_replicate.run.assert_called()
        
        # Verify Save called
        mock_save.assert_called_with("http://example.com/image.png")

if __name__ == '__main__':
    unittest.main()
