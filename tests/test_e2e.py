#!/usr/bin/env python3
"""
End-to-End Tests for Repo-Artist

Tests the full pipeline:
1. API health check
2. Preview endpoint (GitHub API tree fetch + architecture analysis + image generation)
3. CLI generate command
"""

import os
import sys
import json
import asyncio
import tempfile
import shutil
from pathlib import Path

import httpx
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
# Use a repo with actual code files for meaningful testing
TEST_REPO_URL = "https://github.com/expressjs/express"  # Well-known public repo with code


class TestE2EHealthCheck:
    """Test basic API health."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test that the API is running and healthy."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            print("✅ Health check passed")
    
    @pytest.mark.asyncio
    async def test_config_endpoint(self):
        """Test that config endpoint returns expected structure."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/config")
            assert response.status_code == 200
            data = response.json()
            assert "has_env_key" in data
            print(f"✅ Config endpoint passed (has_env_key: {data['has_env_key']})")


class TestE2EPreviewEndpoint:
    """Test the preview endpoint with GitHub API integration."""
    
    @pytest.mark.asyncio
    async def test_preview_generates_architecture(self):
        """
        Full E2E test: 
        1. Calls /api/preview with a real GitHub repo
        2. Verifies architecture analysis works
        3. Verifies image generation works
        """
        async with httpx.AsyncClient(timeout=180.0) as client:
            print(f"\n🔄 Testing preview endpoint with {TEST_REPO_URL}...")
            
            response = await client.post(
                f"{BASE_URL}/api/preview",
                json={
                    "repo_url": TEST_REPO_URL,
                    "style": "auto",
                    "force_reanalyze": True
                }
            )
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   Error: {response.text[:500]}")
                # Don't fail if API key is missing - that's expected in some environments
                if "API Key is required" in response.text:
                    pytest.skip("GEMINI_API_KEY not configured - skipping full E2E test")
                    return
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
            
            data = response.json()
            
            # Verify architecture was analyzed
            assert "architecture" in data, "Response should contain architecture"
            architecture = data["architecture"]
            assert "system_summary" in architecture, "Architecture should have system_summary"
            assert "components" in architecture, "Architecture should have components"
            print(f"   ✅ Architecture analyzed: {len(architecture.get('components', []))} components")
            print(f"   Summary: {architecture.get('system_summary', 'N/A')[:100]}...")
            
            # Verify image was generated
            assert "image_b64" in data, "Response should contain image_b64"
            assert data["image_b64"] is not None, "image_b64 should not be None"
            assert len(data["image_b64"]) > 1000, "image_b64 should be substantial"
            print(f"   ✅ Image generated: {len(data['image_b64'])} bytes (base64)")
            
            # Verify README preview
            assert "new_readme" in data, "Response should contain new_readme"
            assert "architecture_diagram" in data["new_readme"], "README should reference the diagram"
            print("   ✅ README preview generated")
            
            print("✅ Full preview E2E test passed!")


class TestE2EGitHubAPIIntegration:
    """Test the new GitHub API integration (no cloning)."""
    
    @pytest.mark.asyncio
    async def test_github_tree_fetch(self):
        """Test that we can fetch repo tree via GitHub API."""
        from web.backend.github_utils import get_repo_tree, tree_to_code_context
        
        print("\n🔄 Testing GitHub API tree fetch...")
        
        # Test with a small public repo
        tree = await get_repo_tree("octocat", "Hello-World", token=None, branch="master")
        
        assert tree is not None, "Tree should not be None"
        assert len(tree) > 0, "Tree should have entries"
        print(f"   ✅ Fetched {len(tree)} entries from GitHub API")
        
        # Test tree to context conversion
        context = tree_to_code_context(tree)
        assert context is not None, "Context should not be None"
        print(f"   ✅ Converted to code context ({len(context)} chars)")
        print("✅ GitHub API integration test passed!")
    
    @pytest.mark.asyncio
    async def test_github_file_content_fetch(self):
        """Test that we can fetch file content via GitHub API."""
        from web.backend.github_utils import get_file_content
        
        print("\n🔄 Testing GitHub API file content fetch...")
        
        # Fetch README from Hello-World repo
        content = await get_file_content("octocat", "Hello-World", "README", branch="master")
        
        assert content is not None, "Content should not be None"
        assert "Hello World" in content, "README should contain 'Hello World'"
        print(f"   ✅ Fetched README ({len(content)} chars)")
        print("✅ GitHub file content fetch test passed!")


class TestE2ECLIGenerate:
    """Test the CLI generate command."""
    
    def test_cli_module_imports(self):
        """Test that CLI module imports work correctly."""
        print("\n🔄 Testing CLI module imports...")
        
        # Test imports
        from scripts.cli import cmd_generate, cmd_setup_ci, ensure_api_key
        from repo_artist.core import get_code_context, analyze_architecture, build_hero_prompt
        from repo_artist.config import RepoArtistConfig, DEFAULT_MODEL
        
        # Verify constants are accessible
        assert DEFAULT_MODEL == "gemini-2.5-flash"
        print(f"   ✅ DEFAULT_MODEL: {DEFAULT_MODEL}")
        
        # Verify config works
        config = RepoArtistConfig()
        assert config.gemini_model == DEFAULT_MODEL
        print(f"   ✅ Config initialized with model: {config.gemini_model}")
        
        print("✅ CLI module imports test passed!")
    
    def test_cli_code_context_generation(self):
        """Test that code context generation works on this repo."""
        print("\n🔄 Testing code context generation...")
        
        from repo_artist.core import get_code_context
        
        # Use the repo-artist project itself
        repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        context = get_code_context(repo_path)
        
        assert context is not None, "Context should not be None"
        assert len(context) > 100, "Context should be substantial"
        assert "📁" in context or "📄" in context, "Context should have file/folder markers"
        
        print(f"   ✅ Generated context ({len(context)} chars)")
        print("✅ Code context generation test passed!")


class TestE2ERichUI:
    """Test that Rich UI components work."""
    
    def test_rich_imports(self):
        """Test that Rich library imports work in CLI."""
        print("\n🔄 Testing Rich UI imports...")
        
        from rich.console import Console
        from rich.panel import Panel
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from rich.prompt import Prompt, Confirm
        from rich.table import Table
        
        # Create a console and test basic functionality
        console = Console(force_terminal=True)
        
        # Test panel creation
        panel = Panel("Test content", title="Test Panel")
        assert panel is not None
        
        # Test table creation
        table = Table()
        table.add_column("Test")
        table.add_row("Value")
        assert table is not None
        
        print("   ✅ All Rich components imported and work")
        print("✅ Rich UI test passed!")


def run_all_tests():
    """Run all E2E tests."""
    print("=" * 60)
    print("🚀 REPO-ARTIST E2E TEST SUITE")
    print("=" * 60)
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--asyncio-mode=auto"
    ])
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
