"""Tests for Repo-Artist pipeline."""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import json
from repo_artist import core as repo_artist


class TestRepoArtist(unittest.TestCase):

    def test_get_code_context_returns_string(self):
        """Test that get_code_context returns a string."""
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('.', [], ['test.py'])]
            result = repo_artist.get_code_context('.')
            self.assertIsInstance(result, str)

    def test_build_hero_prompt_with_valid_architecture(self):
        """Test build_hero_prompt with valid input includes correct format."""
        arch = {
            "system_summary": "A test system for testing",
            "components": [
                {"id": "a", "label": "Component A", "type": "api", "role": "Handles requests"},
                {"id": "b", "label": "Component B", "type": "database", "role": "Stores data"}
            ],
            "connections": [
                {"from": "a", "to": "b", "label": "queries data"}
            ]
        }
        result = repo_artist.build_hero_prompt(arch)
        
        # Check for Nano Banana style format
        self.assertIn("hyper-realistic, premium 3D", result)
        self.assertIn("System: A test system for testing", result)
        self.assertIn("'Component A'", result)
        self.assertIn("'Component B'", result)
        self.assertIn("data pipe flows from", result)
        self.assertIn("ENSURE ALL TEXT LABELS ARE PERFECTLY LEGIBLE", result)

    def test_build_hero_prompt_with_style(self):
        """Test build_hero_prompt with custom style variation."""
        arch = {
            "system_summary": "Test",
            "components": [{"id": "a", "label": "A", "type": "api", "role": "test"}],
            "connections": []
        }
        result = repo_artist.build_hero_prompt(arch, hero_style="more neon")
        self.assertIn("more neon", result)

    def test_build_hero_prompt_handles_none(self):
        """Test build_hero_prompt with None."""
        result = repo_artist.build_hero_prompt(None)
        self.assertIsNone(result)

    def test_architecture_to_mermaid(self):
        """Test mermaid code generation."""
        arch = {
            "components": [{"id": "a", "label": "A", "type": "api", "role": ""}],
            "connections": []
        }
        result = repo_artist.architecture_to_mermaid(arch)
        self.assertIn("graph LR", result)

    def test_save_and_load_architecture_cache(self):
        """Test architecture caching functions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "test_cache.json")
            test_arch = {"system_summary": "Test", "components": [], "connections": []}
            
            # Save
            result = repo_artist.save_architecture_cache(test_arch, cache_path)
            self.assertTrue(result)
            
            # Load
            loaded = repo_artist.load_cached_architecture(cache_path)
            self.assertEqual(loaded["system_summary"], "Test")

    def test_generate_hero_image_pollinations_exists(self):
        """Test that generate_hero_image_pollinations function exists."""
        self.assertTrue(callable(repo_artist.generate_hero_image_pollinations))

    @patch('repo_artist.core.requests.get')
    def test_generate_hero_image_pollinations_success(self, mock_get):
        """Test generating hero image via Pollinations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_content"
        mock_get.return_value = mock_response

        prompt = "test prompt"
        result = repo_artist.generate_hero_image_pollinations(prompt)

        self.assertEqual(result, b"fake_image_content")
        mock_get.assert_called()
        # Verify URL structure
        args, _ = mock_get.call_args
        self.assertIn("pollinations.ai", args[0])
        self.assertIn("test%20prompt", args[0])


if __name__ == '__main__':
    unittest.main()
