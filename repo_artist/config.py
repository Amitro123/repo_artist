"""
Repo-Artist Configuration Module

Centralizes all configuration options with support for:
- Environment variables
- .artistignore file for custom ignore patterns
- Sensible defaults
"""

import os
import logging
from pathlib import Path
from typing import Set, Optional
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class RepoArtistConfig:
    """Configuration for Repo-Artist with all customizable options."""
    
    # API Configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    imagen_project_id: Optional[str] = None
    imagen_location: str = "us-central1"
    force_reanalyze: bool = False  # Added for caching control
    
    # Analysis Configuration
    max_depth: int = 3
    max_components: int = 7
    max_connections: int = 7
    
    # Paths Configuration
    output_dir: str = "assets"
    output_image_name: str = "architecture_diagram.png"
    cache_file_name: str = "architecture.json"
    repo_json_name: str = "repo-artist-architecture.json"
    artistignore_file: str = ".artistignore"
    
    # File Patterns
    ignore_dirs: Set[str] = field(default_factory=lambda: {
        '.git', 'node_modules', 'venv', '.venv', '__pycache__', 
        'assets', '.github', '.idea', 'tests', 'dist', 'build',
        'coverage', '.pytest_cache', '.mypy_cache', '.tox', 'eggs'
    })
    
    important_extensions: Set[str] = field(default_factory=lambda: {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.rb',
        '.json', '.md', '.yml', '.yaml', '.toml', '.sql', '.sh', '.dockerfile'
    })
    
    important_files: Set[str] = field(default_factory=lambda: {
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        'Makefile', 'requirements.txt', 'package.json', 'Cargo.toml',
        'go.mod', 'pom.xml', 'build.gradle'
    })
    
    # Image Generation URLs (configurable to avoid hardcoding)
    pollinations_url: str = "https://image.pollinations.ai/prompt/{prompt}"
    pollinations_width: int = 1280
    pollinations_height: int = 720
    mermaid_ink_url: str = "https://mermaid.ink/img/{encoded}"
    
    # Retry Configuration
    max_json_retries: int = 3
    
    @classmethod
    def from_env(cls, repo_path: str = ".") -> "RepoArtistConfig":
        """
        Create configuration from environment variables and .artistignore file.
        
        Args:
            repo_path: Path to repository root for loading .artistignore
            
        Returns:
            RepoArtistConfig instance
        """
        config = cls()
        
        # Load from environment variables
        config.gemini_api_key = os.getenv("GEMINI_API_KEY")
        config.gemini_model = os.getenv("ARCH_MODEL_NAME", config.gemini_model)
        config.imagen_project_id = os.getenv("IMAGEN_PROJECT_ID")
        config.imagen_location = os.getenv("IMAGEN_LOCATION", config.imagen_location)
        
        # Load numeric configurations
        if max_depth := os.getenv("REPO_ARTIST_MAX_DEPTH"):
            try:
                config.max_depth = int(max_depth)
            except ValueError:
                logger.warning(f"Invalid REPO_ARTIST_MAX_DEPTH value: {max_depth}, using default")
        
        if max_components := os.getenv("REPO_ARTIST_MAX_COMPONENTS"):
            try:
                config.max_components = int(max_components)
            except ValueError:
                logger.warning(f"Invalid REPO_ARTIST_MAX_COMPONENTS value: {max_components}, using default")
        
        if max_connections := os.getenv("REPO_ARTIST_MAX_CONNECTIONS"):
            try:
                config.max_connections = int(max_connections)
            except ValueError:
                logger.warning(f"Invalid REPO_ARTIST_MAX_CONNECTIONS value: {max_connections}, using default")
        
        # Load path configurations
        config.output_dir = os.getenv("REPO_ARTIST_OUTPUT_DIR", config.output_dir)
        config.output_image_name = os.getenv("REPO_ARTIST_IMAGE_NAME", config.output_image_name)
        
        # Load custom ignore patterns from .artistignore
        config._load_artistignore(repo_path)
        
        return config
    
    def _load_artistignore(self, repo_path: str) -> None:
        """
        Load custom ignore patterns from .artistignore file.
        
        Format is similar to .gitignore:
        - Lines starting with # are comments
        - Empty lines are ignored
        - Each line is a directory or file pattern to ignore
        """
        artistignore_path = Path(repo_path) / self.artistignore_file
        
        if not artistignore_path.exists():
            return
        
        try:
            with open(artistignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Add to ignore_dirs
                    self.ignore_dirs.add(line)
            
            logger.info(f"Loaded custom ignore patterns from {artistignore_path}")
        except Exception as e:
            logger.warning(f"Failed to load .artistignore: {e}")
    
    def get_output_image_path(self, repo_path: str = ".") -> str:
        """Get full path to output image file."""
        return os.path.join(repo_path, self.output_dir, self.output_image_name)
    
    def get_cache_path(self, repo_path: str = ".") -> str:
        """Get full path to cache file."""
        return os.path.join(repo_path, self.output_dir, self.cache_file_name)
    
    def get_repo_json_path(self, repo_path: str = ".") -> str:
        """Get full path to persistent repo JSON file."""
        return os.path.join(repo_path, self.repo_json_name)
