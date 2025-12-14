"""
Tests for multi-tier image generation system
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repo_artist.core import (
    generate_hero_image,
    generate_hero_image_imagen3,
    generate_hero_image_pollinations,
    generate_hero_image_mermaid
)
from repo_artist.config import RepoArtistConfig


class TestMultiTierImageGeneration(unittest.TestCase):
    
    @patch('repo_artist.core.generate_hero_image_imagen3')
    @patch('repo_artist.core.generate_hero_image_pollinations')
    @patch('repo_artist.core.generate_hero_image_mermaid')
    def test_tier1_success(self, mock_mermaid, mock_pollinations, mock_imagen3):
        """Test that Tier 1 (Imagen 3) is tried first and used if successful."""
        mock_imagen3.return_value = b"imagen3_image_data"
        
        architecture = {"components": [], "connections": []}
        result = generate_hero_image("test prompt", architecture)
        
        # Should return Tier 1 result
        self.assertEqual(result, b"imagen3_image_data")
        # Should not try other tiers
        mock_pollinations.assert_not_called()
        mock_mermaid.assert_not_called()
    
    @patch('repo_artist.core.generate_hero_image_imagen3')
    @patch('repo_artist.core.generate_hero_image_pollinations')
    @patch('repo_artist.core.generate_hero_image_mermaid')
    def test_tier1_fails_tier2_success(self, mock_mermaid, mock_pollinations, mock_imagen3):
        """Test fallback to Tier 2 when Tier 1 fails."""
        mock_imagen3.return_value = None  # Tier 1 fails
        mock_pollinations.return_value = b"pollinations_image_data"
        
        architecture = {"components": [], "connections": []}
        result = generate_hero_image("test prompt", architecture)
        
        # Should return Tier 2 result
        self.assertEqual(result, b"pollinations_image_data")
        # Should have tried Tier 1 first
        mock_imagen3.assert_called_once()
        # Should not try Tier 3
        mock_mermaid.assert_not_called()
    
    @patch('repo_artist.core.generate_hero_image_imagen3')
    @patch('repo_artist.core.generate_hero_image_pollinations')
    @patch('repo_artist.core.generate_hero_image_mermaid')
    def test_tier1_tier2_fail_tier3_success(self, mock_mermaid, mock_pollinations, mock_imagen3):
        """Test fallback to Tier 3 when Tier 1 and 2 fail."""
        mock_imagen3.return_value = None  # Tier 1 fails
        mock_pollinations.return_value = None  # Tier 2 fails
        mock_mermaid.return_value = b"mermaid_diagram_data"
        
        architecture = {"components": [], "connections": []}
        result = generate_hero_image("test prompt", architecture)
        
        # Should return Tier 3 result
        self.assertEqual(result, b"mermaid_diagram_data")
        # Should have tried all tiers
        mock_imagen3.assert_called_once()
        mock_pollinations.assert_called_once()
        mock_mermaid.assert_called_once()


class TestImagen3Generation(unittest.TestCase):
    
    def test_imagen3_without_project_id(self):
        """Test that Imagen 3 returns None when project ID is not configured."""
        config = RepoArtistConfig()
        config.imagen_project_id = None
        
        result = generate_hero_image_imagen3("test prompt", config=config)
        
        self.assertIsNone(result)
    
    def test_imagen3_import_error_handling(self):
        """Test that Imagen 3 handles missing google-cloud-aiplatform gracefully."""
        config = RepoArtistConfig()
        config.imagen_project_id = "test-project"
        
        # Should return None if package is not installed (ImportError)
        # This is expected behavior
        result = generate_hero_image_imagen3("test prompt", config=config)
        
        # Will be None if package not installed, which is fine
        # The function handles ImportError internally
        self.assertIsNone(result)


class TestPollinationsGeneration(unittest.TestCase):
    
    @patch('repo_artist.core.requests.get')
    def test_pollinations_success(self, mock_get):
        """Test successful image generation from Pollinations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"pollinations_image_data"
        mock_get.return_value = mock_response
        
        result = generate_hero_image_pollinations("test prompt")
        
        self.assertEqual(result, b"pollinations_image_data")
        mock_get.assert_called_once()
    
    @patch('repo_artist.core.requests.get')
    def test_pollinations_retry_on_server_error(self, mock_get):
        """Test that Pollinations retries on server errors."""
        # First two calls fail with 503, third succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.content = b"pollinations_image_data"
        
        mock_get.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ]
        
        result = generate_hero_image_pollinations("test prompt")
        
        self.assertEqual(result, b"pollinations_image_data")
        # Should have retried 3 times
        self.assertEqual(mock_get.call_count, 3)
    
    @patch('repo_artist.core.requests.get')
    def test_pollinations_max_retries_exceeded(self, mock_get):
        """Test that Pollinations returns None after max retries."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        
        result = generate_hero_image_pollinations("test prompt")
        
        self.assertIsNone(result)
        # Should have tried 3 times
        self.assertEqual(mock_get.call_count, 3)
    
    @patch('repo_artist.core.requests.get')
    def test_pollinations_handles_connection_error(self, mock_get):
        """Test that Pollinations handles connection errors gracefully."""
        mock_get.side_effect = Exception("Connection error")
        
        result = generate_hero_image_pollinations("test prompt")
        
        self.assertIsNone(result)


class TestMermaidGeneration(unittest.TestCase):
    
    @patch('repo_artist.core.requests.get')
    def test_mermaid_success(self, mock_get):
        """Test successful diagram generation from mermaid.ink."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"mermaid_diagram_data"
        mock_get.return_value = mock_response
        
        architecture = {
            "components": [
                {"id": "comp1", "label": "Component 1", "type": "backend"}
            ],
            "connections": []
        }
        
        result = generate_hero_image_mermaid(architecture)
        
        self.assertEqual(result, b"mermaid_diagram_data")
        mock_get.assert_called_once()
    
    @patch('repo_artist.core.requests.get')
    def test_mermaid_handles_error(self, mock_get):
        """Test that mermaid generation handles errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        architecture = {
            "components": [{"id": "comp1", "label": "Component 1", "type": "backend"}],
            "connections": []
        }
        
        result = generate_hero_image_mermaid(architecture)
        
        self.assertIsNone(result)
    
    def test_mermaid_with_empty_architecture(self):
        """Test mermaid generation with empty architecture."""
        result = generate_hero_image_mermaid(None)
        self.assertIsNone(result)


class TestImageGenerationIntegration(unittest.TestCase):
    
    @patch('repo_artist.core.requests.get')
    def test_end_to_end_fallback_to_mermaid(self, mock_get):
        """Test complete fallback chain ending with Mermaid."""
        # Mock all requests to fail except the last one (Mermaid)
        mock_fail_response = MagicMock()
        mock_fail_response.status_code = 500
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.content = b"mermaid_diagram"
        
        # Return failures for Pollinations attempts, then success for Mermaid
        def side_effect(*args, **kwargs):
            # Check if this is a Mermaid request (contains mermaid.ink)
            if 'mermaid.ink' in args[0]:
                return mock_success_response
            else:
                return mock_fail_response
        
        mock_get.side_effect = side_effect
        
        architecture = {
            "components": [{"id": "comp1", "label": "Component 1", "type": "backend"}],
            "connections": []
        }
        
        result = generate_hero_image("test prompt", architecture)
        
        # Should eventually get Mermaid diagram
        self.assertIsNotNone(result)
        self.assertEqual(result, b"mermaid_diagram")
        # Should have made multiple attempts
        self.assertGreater(mock_get.call_count, 1)


if __name__ == '__main__':
    unittest.main()
