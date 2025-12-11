"""Tests for Repo-Artist pipeline."""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import repo_artist


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
        
        # Check for exact style template elements
        self.assertIn("System overview:", result)
        self.assertIn("Components as floating platforms:", result)
        self.assertIn("Data flows between platforms:", result)
        self.assertIn("Visual style requirements:", result)
        self.assertIn('Platform 1: Label "Component A"', result)
        self.assertIn('Arrow from "Component A" to "Component B"', result)

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

    def test_generate_hero_image_exists(self):
        """Test that generate_hero_image function exists."""
        self.assertTrue(callable(repo_artist.generate_hero_image))


if __name__ == '__main__':
    unittest.main()
