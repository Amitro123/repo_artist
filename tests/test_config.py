"""
Tests for the configuration system (repo_artist/config.py)
"""

import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repo_artist.config import RepoArtistConfig


class TestRepoArtistConfig(unittest.TestCase):
    
    def test_default_config(self):
        """Test that default configuration has sensible values."""
        config = RepoArtistConfig()
        
        self.assertEqual(config.gemini_model, "gemini-2.5-flash")
        self.assertEqual(config.max_depth, 3)
        self.assertEqual(config.max_components, 7)
        self.assertEqual(config.max_connections, 7)
        self.assertEqual(config.output_dir, "assets")
        self.assertEqual(config.output_image_name, "architecture_diagram.png")
        self.assertIn('.git', config.ignore_dirs)
        self.assertIn('.py', config.important_extensions)
    
    @patch.dict(os.environ, {
        'GEMINI_API_KEY': 'test_key_123',
        'ARCH_MODEL_NAME': 'gemini-2.0-flash',
        'IMAGEN_PROJECT_ID': 'test-project',
        'IMAGEN_LOCATION': 'us-west1',
        'REPO_ARTIST_MAX_DEPTH': '5',
        'REPO_ARTIST_MAX_COMPONENTS': '10',
        'REPO_ARTIST_MAX_CONNECTIONS': '12',
        'REPO_ARTIST_OUTPUT_DIR': 'output'
    })
    def test_from_env(self):
        """Test loading configuration from environment variables."""
        config = RepoArtistConfig.from_env()
        
        self.assertEqual(config.gemini_api_key, 'test_key_123')
        self.assertEqual(config.gemini_model, 'gemini-2.0-flash')
        self.assertEqual(config.imagen_project_id, 'test-project')
        self.assertEqual(config.imagen_location, 'us-west1')
        self.assertEqual(config.max_depth, 5)
        self.assertEqual(config.max_components, 10)
        self.assertEqual(config.max_connections, 12)
        self.assertEqual(config.output_dir, 'output')
    
    @patch.dict(os.environ, {
        'REPO_ARTIST_MAX_DEPTH': 'invalid',
        'REPO_ARTIST_MAX_COMPONENTS': 'not_a_number'
    })
    def test_from_env_invalid_numbers(self):
        """Test that invalid numeric env vars fall back to defaults."""
        config = RepoArtistConfig.from_env()
        
        # Should fall back to defaults
        self.assertEqual(config.max_depth, 3)
        self.assertEqual(config.max_components, 7)
    
    def test_artistignore_loading(self):
        """Test loading custom ignore patterns from .artistignore file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .artistignore file
            artistignore_path = Path(tmpdir) / '.artistignore'
            with open(artistignore_path, 'w') as f:
                f.write("# Comment line\n")
                f.write("\n")  # Empty line
                f.write("vendor\n")
                f.write("third_party\n")
                f.write("legacy_code\n")
            
            config = RepoArtistConfig.from_env(tmpdir)
            
            # Should include default patterns
            self.assertIn('.git', config.ignore_dirs)
            # Should include custom patterns
            self.assertIn('vendor', config.ignore_dirs)
            self.assertIn('third_party', config.ignore_dirs)
            self.assertIn('legacy_code', config.ignore_dirs)
    
    def test_artistignore_missing(self):
        """Test that missing .artistignore doesn't cause errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = RepoArtistConfig.from_env(tmpdir)
            # Should still have default patterns
            self.assertIn('.git', config.ignore_dirs)
    
    def test_get_output_image_path(self):
        """Test output image path generation."""
        config = RepoArtistConfig()
        path = config.get_output_image_path("/test/repo")
        
        expected = os.path.join("/test/repo", "assets", "architecture_diagram.png")
        self.assertEqual(path, expected)
    
    def test_get_cache_path(self):
        """Test cache path generation."""
        config = RepoArtistConfig()
        path = config.get_cache_path("/test/repo")
        
        expected = os.path.join("/test/repo", "assets", "architecture.json")
        self.assertEqual(path, expected)
    
    def test_get_repo_json_path(self):
        """Test repo JSON path generation."""
        config = RepoArtistConfig()
        path = config.get_repo_json_path("/test/repo")
        
        expected = os.path.join("/test/repo", "repo-artist-architecture.json")
        self.assertEqual(path, expected)
    
    def test_custom_output_paths(self):
        """Test custom output directory configuration."""
        config = RepoArtistConfig()
        config.output_dir = "custom_output"
        config.output_image_name = "diagram.png"
        
        path = config.get_output_image_path("/test/repo")
        expected = os.path.join("/test/repo", "custom_output", "diagram.png")
        self.assertEqual(path, expected)


if __name__ == '__main__':
    unittest.main()
