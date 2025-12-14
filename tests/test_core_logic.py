"""
Tests for core logic improvements (repo_artist/core.py)
"""

import unittest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repo_artist.core import (
    get_code_context,
    analyze_architecture,
    build_hero_prompt,
    update_readme_content,
    _clean_json_response,
    architecture_to_mermaid,
    configure_gemini,
    load_cached_architecture,
    save_architecture_cache,
    load_architecture_json,
    save_architecture_json
)
from repo_artist.config import RepoArtistConfig


class TestCodeContext(unittest.TestCase):
    
    def test_get_code_context_with_custom_depth(self):
        """Test that custom max_depth is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            Path(tmpdir, "level1", "level2", "level3", "level4").mkdir(parents=True)
            Path(tmpdir, "level1", "test.py").touch()
            Path(tmpdir, "level1", "level2", "test.py").touch()
            Path(tmpdir, "level1", "level2", "level3", "test.py").touch()
            Path(tmpdir, "level1", "level2", "level3", "level4", "test.py").touch()
            
            config = RepoArtistConfig()
            config.max_depth = 2
            
            result = get_code_context(tmpdir, config)
            
            # Should include level1 and level2, but not level3 or level4
            self.assertIn("level1", result)
            self.assertIn("level2", result)
            # Level 3 should be excluded due to depth limit
            self.assertNotIn("level4", result)
    
    def test_get_code_context_respects_ignore_dirs(self):
        """Test that ignore_dirs configuration is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directories
            Path(tmpdir, "src").mkdir()
            Path(tmpdir, "node_modules").mkdir()
            Path(tmpdir, "custom_ignore").mkdir()
            
            Path(tmpdir, "src", "test.py").touch()
            Path(tmpdir, "node_modules", "test.js").touch()
            Path(tmpdir, "custom_ignore", "test.py").touch()
            
            config = RepoArtistConfig()
            config.ignore_dirs.add("custom_ignore")
            
            result = get_code_context(tmpdir, config)
            
            # Should include src
            self.assertIn("src", result)
            # Should not include node_modules (default ignore)
            self.assertNotIn("node_modules", result)
            # Should not include custom_ignore
            self.assertNotIn("custom_ignore", result)
    
    def test_get_code_context_respects_important_extensions(self):
        """Test that important_extensions configuration is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test.py").touch()
            Path(tmpdir, "test.js").touch()
            Path(tmpdir, "test.txt").touch()
            Path(tmpdir, "test.custom").touch()
            
            config = RepoArtistConfig()
            config.important_extensions = {'.py', '.custom'}
            
            result = get_code_context(tmpdir, config)
            
            # Should include .py and .custom
            self.assertIn("test.py", result)
            self.assertIn("test.custom", result)
            # Should not include .txt
            self.assertNotIn("test.txt", result)


class TestJSONParsing(unittest.TestCase):
    
    def test_clean_json_response_with_markdown(self):
        """Test cleaning JSON response with markdown code fences."""
        raw = "```json\n{\"test\": \"value\"}\n```"
        cleaned = _clean_json_response(raw)
        self.assertEqual(cleaned, '{"test": "value"}')
    
    def test_clean_json_response_without_json_tag(self):
        """Test cleaning JSON response with code fences but no json tag."""
        raw = "```\n{\"test\": \"value\"}\n```"
        cleaned = _clean_json_response(raw)
        self.assertEqual(cleaned, '{"test": "value"}')
    
    def test_clean_json_response_plain(self):
        """Test cleaning plain JSON response."""
        raw = '{"test": "value"}'
        cleaned = _clean_json_response(raw)
        self.assertEqual(cleaned, '{"test": "value"}')
    
    @patch('repo_artist.core.genai')
    def test_analyze_architecture_retry_on_json_error(self, mock_genai):
        """Test that analyze_architecture retries on JSON parse errors."""
        # Setup mock
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        # First two calls return invalid JSON, third returns valid
        mock_response1 = MagicMock()
        mock_response1.text = "This is not JSON"
        
        mock_response2 = MagicMock()
        mock_response2.text = "{invalid json"
        
        mock_response3 = MagicMock()
        mock_response3.text = '{"system_summary": "Test", "components": [], "connections": []}'
        
        mock_model.generate_content.side_effect = [
            mock_response1,
            mock_response2,
            mock_response3
        ]
        
        config = RepoArtistConfig()
        config.max_json_retries = 3
        
        result = analyze_architecture(
            "test context",
            "test_api_key",
            config=config
        )
        
        # Should succeed on third try
        self.assertIsNotNone(result)
        self.assertEqual(result["system_summary"], "Test")
        # Should have called generate_content 3 times
        self.assertEqual(mock_model.generate_content.call_count, 3)
    
    @patch('repo_artist.core.genai')
    def test_analyze_architecture_max_retries_exceeded(self, mock_genai):
        """Test that analyze_architecture returns None after max retries."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Always return invalid JSON
        mock_response = MagicMock()
        mock_response.text = "Not valid JSON"
        mock_model.generate_content.return_value = mock_response
        
        config = RepoArtistConfig()
        config.max_json_retries = 3
        
        result = analyze_architecture(
            "test context",
            "test_api_key",
            config=config
        )
        
        # Should return None after all retries
        self.assertIsNone(result)
        # Should have tried max_json_retries times
        self.assertEqual(mock_model.generate_content.call_count, 3)


class TestBuildHeroPrompt(unittest.TestCase):
    
    def test_build_hero_prompt_respects_max_components(self):
        """Test that max_components limit is respected."""
        architecture = {
            "system_summary": "Test system",
            "components": [
                {"id": f"comp{i}", "label": f"Component {i}", "type": "backend", "role": "Test"}
                for i in range(10)
            ],
            "connections": []
        }
        
        config = RepoArtistConfig()
        config.max_components = 3
        
        prompt = build_hero_prompt(architecture, config=config)
        
        # Should only include 3 components
        self.assertIn("Component 0", prompt)
        self.assertIn("Component 1", prompt)
        self.assertIn("Component 2", prompt)
        self.assertNotIn("Component 3", prompt)
    
    def test_build_hero_prompt_respects_max_connections(self):
        """Test that max_connections limit is respected."""
        architecture = {
            "system_summary": "Test system",
            "components": [
                {"id": "comp1", "label": "Component 1", "type": "backend", "role": "Test"},
                {"id": "comp2", "label": "Component 2", "type": "frontend", "role": "Test"}
            ],
            "connections": [
                {"from": "comp1", "to": "comp2", "label": f"Connection {i}"}
                for i in range(10)
            ]
        }
        
        config = RepoArtistConfig()
        config.max_connections = 3
        
        prompt = build_hero_prompt(architecture, config=config)
        
        # Should only include 3 connections
        self.assertIn("Connection 0", prompt)
        self.assertIn("Connection 1", prompt)
        self.assertIn("Connection 2", prompt)
        self.assertNotIn("Connection 3", prompt)
    
    def test_build_hero_prompt_with_style(self):
        """Test that custom style is appended to prompt."""
        architecture = {
            "system_summary": "Test system",
            "components": [],
            "connections": []
        }
        
        prompt = build_hero_prompt(architecture, hero_style="cyberpunk neon")
        
        self.assertIn("cyberpunk neon", prompt)


class TestReadmeUpdate(unittest.TestCase):
    
    def test_update_readme_content_empty(self):
        """Test updating empty README."""
        result = update_readme_content("", "assets/test.png")
        
        self.assertIn("![Architecture](assets/test.png)", result)
        self.assertIn("# Project", result)
    
    def test_update_readme_content_already_exists(self):
        """Test that existing image reference is not duplicated."""
        original = "# Test\n\n![Architecture](assets/test.png)\n\nContent"
        result = update_readme_content(original, "assets/test.png")
        
        # Should return unchanged
        self.assertEqual(result, original)
    
    def test_update_readme_content_insert_after_title(self):
        """Test inserting image after title."""
        original = "# My Project\n\nSome description here."
        result = update_readme_content(original, "assets/test.png")
        
        self.assertIn("![Architecture](assets/test.png)", result)
        # Image should come after title
        lines = result.split('\n')
        title_idx = lines.index("# My Project")
        image_line = "![Architecture](assets/test.png)"
        image_idx = next(i for i, line in enumerate(lines) if image_line in line)
        self.assertGreater(image_idx, title_idx)
    
    def test_update_readme_content_skip_badges(self):
        """Test that image is inserted after badges."""
        original = """# My Project

[![Build](https://img.shields.io/badge/build-passing-green)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

Description here."""
        
        result = update_readme_content(original, "assets/test.png")
        
        self.assertIn("![Architecture](assets/test.png)", result)
        # Should be after badges
        self.assertIn("[![License", result)
    
    def test_update_readme_content_replace_existing(self):
        """Test replacing existing architecture diagram."""
        original = "# Test\n\n![Old Diagram](assets/architecture_diagram.png)\n\nContent"
        result = update_readme_content(original, "assets/architecture_diagram.png")
        
        # Should update the existing reference
        self.assertIn("![Architecture](assets/architecture_diagram.png)", result)
        self.assertNotIn("![Old Diagram]", result)


class TestCaching(unittest.TestCase):
    
    def test_save_and_load_architecture_cache(self):
        """Test saving and loading architecture cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "cache", "architecture.json")
            
            architecture = {
                "system_summary": "Test system",
                "components": [{"id": "test", "label": "Test", "type": "backend", "role": "Test"}],
                "connections": []
            }
            
            # Save
            result = save_architecture_cache(architecture, cache_path)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(cache_path))
            
            # Load
            loaded = load_cached_architecture(cache_path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["system_summary"], "Test system")
    
    def test_load_cached_architecture_missing(self):
        """Test loading missing cache returns None."""
        result = load_cached_architecture("/nonexistent/path.json")
        self.assertIsNone(result)
    
    def test_save_and_load_architecture_json(self):
        """Test saving and loading repo architecture JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            architecture = {
                "system_summary": "Test system",
                "components": [],
                "connections": []
            }
            
            # Save
            result = save_architecture_json(architecture, tmpdir)
            self.assertTrue(result)
            
            expected_path = os.path.join(tmpdir, "repo-artist-architecture.json")
            self.assertTrue(os.path.exists(expected_path))
            
            # Load
            loaded = load_architecture_json(tmpdir)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["system_summary"], "Test system")


class TestMermaidGeneration(unittest.TestCase):
    
    def test_architecture_to_mermaid(self):
        """Test converting architecture to Mermaid diagram."""
        architecture = {
            "components": [
                {"id": "frontend", "label": "Frontend", "type": "frontend"},
                {"id": "backend", "label": "Backend", "type": "backend"},
                {"id": "database", "label": "Database", "type": "database"}
            ],
            "connections": [
                {"from": "frontend", "to": "backend"},
                {"from": "backend", "to": "database"}
            ]
        }
        
        mermaid = architecture_to_mermaid(architecture)
        
        self.assertIsNotNone(mermaid)
        self.assertIn("graph LR", mermaid)
        self.assertIn("frontend(Frontend)", mermaid)
        self.assertIn("backend(Backend)", mermaid)
        self.assertIn("database(Database)", mermaid)
        self.assertIn("frontend --> backend", mermaid)
        self.assertIn("backend --> database", mermaid)
    
    def test_architecture_to_mermaid_sanitizes_ids(self):
        """Test that special characters in IDs are sanitized."""
        architecture = {
            "components": [
                {"id": "my-component-1", "label": "Component 1", "type": "backend"}
            ],
            "connections": []
        }
        
        mermaid = architecture_to_mermaid(architecture)
        
        # Should sanitize the ID (remove hyphens)
        self.assertIn("mycomponent1", mermaid)


class TestGeminiConfiguration(unittest.TestCase):
    
    @patch('repo_artist.core.genai')
    def test_configure_gemini_once(self, mock_genai):
        """Test that Gemini is configured only once."""
        # Reset the global state
        import repo_artist.core
        repo_artist.core._gemini_configured = False
        
        configure_gemini("test_key_1")
        configure_gemini("test_key_2")
        configure_gemini("test_key_3")
        
        # Should only configure once
        self.assertEqual(mock_genai.configure.call_count, 1)
        mock_genai.configure.assert_called_once_with(api_key="test_key_1")


if __name__ == '__main__':
    unittest.main()
