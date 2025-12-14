"""
Repo-Artist Core Logic

Contains the pure business logic for harvesting, analysis, and generation.
"""

import os
import re
import json
import urllib.parse
import base64
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import google.generativeai as genai
import requests

from .config import RepoArtistConfig

# --- CONFIGURATION ---
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
MERMAID_INK_URL = "https://mermaid.ink/img/{encoded}"
DEFAULT_MODEL = "gemini-2.5-flash"

# Setup logging
logger = logging.getLogger(__name__)

# Global Gemini configuration state
_gemini_configured = False


def configure_gemini(api_key: str) -> None:
    """
    Configure Gemini API globally.
    
    Args:
        api_key: Gemini API key
    """
    global _gemini_configured
    if not _gemini_configured:
        genai.configure(api_key=api_key)
        _gemini_configured = True
        logger.debug("Gemini API configured")


def get_code_context(root_dir: str = ".", config: Optional[RepoArtistConfig] = None) -> str:
    """
    Step 1: Harvests file structure from the repository.
    
    Args:
        root_dir: Root directory to scan
        config: Configuration object with ignore patterns and depth settings
        
    Returns:
        String representation of the file structure
    """
    if config is None:
        config = RepoArtistConfig.from_env(root_dir)
    
    structure: List[str] = []
    
    logger.info(f"Step 1: Harvesting project structure from {root_dir}...")
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in config.ignore_dirs]
        depth = root.count(os.sep) - root_dir.count(os.sep)
        if depth > config.max_depth:
            continue
            
        indent = "  " * depth
        folder_name = os.path.basename(root)
        if folder_name and folder_name != ".":
            structure.append(f"{indent}📁 {folder_name}/")
        
        for file in files:
            file_lower = file.lower()
            if (Path(file).suffix.lower() in config.important_extensions or 
                file in config.important_files or 
                file_lower in config.important_files):
                structure.append(f"{indent}  📄 {file}")
                
    result = "\n".join(structure)
    logger.info(f"Found {len(structure)} items")
    return result


def load_cached_architecture(cache_path: str) -> Optional[Dict[str, Any]]:
    """
    Loads architecture from cache file if it exists.
    
    Args:
        cache_path: Path to cache file
        
    Returns:
        Architecture dict if successful, None otherwise
    """
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                architecture = json.load(f)
            logger.info(f"Loaded cached architecture from {cache_path}")
            logger.debug(f"Components: {len(architecture.get('components', []))}")
            return architecture
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache: {e}")
    return None


def save_architecture_cache(architecture: Dict[str, Any], cache_path: str) -> bool:
    """
    Saves architecture JSON to cache file.
    
    Args:
        architecture: Architecture dictionary
        cache_path: Path to cache file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(architecture, f, indent=2)
        logger.info(f"Architecture cached to {cache_path}")
        return True
    except IOError as e:
        logger.warning(f"Failed to save cache: {e}")
        return False


def load_architecture_json(repo_path: str) -> Optional[Dict[str, Any]]:
    """
    Loads architecture from repo-artist-architecture.json in the repository root.
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        Architecture dict if found and valid, None otherwise
    """
    json_path = os.path.join(repo_path, "repo-artist-architecture.json")
    
    if not os.path.exists(json_path):
        return None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            architecture = json.load(f)
        logger.info(f"Loaded architecture from {json_path}")
        return architecture
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load repo architecture JSON: {e}")
        return None


def save_architecture_json(architecture: Dict[str, Any], repo_path: str) -> bool:
    """
    Saves architecture to repo-artist-architecture.json in the repository root.
    
    Args:
        architecture: Architecture dictionary
        repo_path: Path to repository root
        
    Returns:
        True if successful, False otherwise
    """
    json_path = os.path.join(repo_path, "repo-artist-architecture.json")
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(architecture, f, indent=2)
        logger.info(f"Saved architecture to {json_path}")
        return True
    except IOError as e:
        logger.warning(f"Failed to save repo architecture JSON: {e}")
        return False


def _clean_json_response(raw_text: str) -> str:
    """
    Clean Gemini response to extract valid JSON.
    
    Args:
        raw_text: Raw response from Gemini
        
    Returns:
        Cleaned JSON string
    """
    raw_text = raw_text.strip()
    
    # Remove markdown code fences
    if raw_text.startswith("```"):
        parts = raw_text.split("```")
        if len(parts) >= 2:
            raw_text = parts[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()
    
    return raw_text


def analyze_architecture(
    code_context: str, 
    api_key: str, 
    model_name: str = "gemini-2.5-flash",
    force_refresh: bool = False, 
    cache_path: Optional[str] = None, 
    force_reanalyze: bool = False, 
    repo_path: Optional[str] = None,
    config: Optional[RepoArtistConfig] = None
) -> Optional[Dict[str, Any]]:
    """
    Step 2: Analyzes code structure and returns JSON architecture via Gemini.
    
    Args:
        code_context: File structure from get_code_context()
        api_key: Gemini API key
        model_name: Gemini model to use
        force_refresh: Ignore local cache (assets/architecture.json)
        cache_path: Path to local cache file
        force_reanalyze: Ignore persistent repo JSON (repo-artist-architecture.json)
        repo_path: Path to repository root for persistent JSON
        config: Configuration object
        
    Returns:
        Architecture dictionary if successful, None otherwise
    """
    if config is None:
        config = RepoArtistConfig.from_env(repo_path or ".")
    
    # Check persistent repo JSON first (unless force_reanalyze)
    if not force_reanalyze and repo_path:
        repo_json = load_architecture_json(repo_path)
        if repo_json:
            logger.info("Using existing architecture from repo-artist-architecture.json")
            return repo_json
    
    # Check local cache second (unless force refresh)
    if not force_refresh and cache_path:
        cached = load_cached_architecture(cache_path)
        if cached:
            return cached
    
    logger.info("Step 2: Analyzing architecture with Gemini...")
    
    if not api_key:
        logger.error("GEMINI_API_KEY not provided")
        return None

    logger.info(f"Using model: {model_name}")
    
    # Configure Gemini globally
    configure_gemini(api_key)
    model = genai.GenerativeModel(model_name)
    
    prompt = '''You are a senior software architect.

You receive a list of files and folders from an arbitrary Git repository.
From this list, infer the HIGH-LEVEL SOFTWARE ARCHITECTURE of the project.

Your ONLY job is to return a STRICTLY VALID JSON OBJECT with this exact structure:

{
  "system_summary": "short 1–2 sentence English description of what this system does",
  "components": [
    {
      "id": "short_alphanumeric_id",
      "label": "Human readable component name",
      "type": "one_of[frontend,backend,api,database,queue,cache,worker,cli,ai_model,external_service,storage,other]",
      "role": "1 sentence describing what this component does",
      "visual_3d_object": "Description of the 3D object (e.g., 'A glowing glass cube')",
      "visual_label": "Description of the label (e.g., 'Floating clearly above it, a flat holographic text label reading 'BACKEND' in bold white sans-serif font.')"
    }
  ],
  "connections": [
    {
      "from": "component_id",
      "to": "component_id",
      "label": "short description of the data or control flow"
    }
  ]
}

Rules you MUST follow:
- Use ONLY the keys: "system_summary", "components", "connections".
- "visual_3d_object" MUST describe the shape/look of the component.
- "visual_label" MUST describe the text label as a separate, floating UI element.
- Use ONLY component IDs that appear in "components".
- Prefer 3–7 components; merge minor pieces into larger logical units.
- Infer common patterns (frontend, backend/api, database, workers, external APIs, AI models, etc.).
- The response MUST be raw JSON: NO markdown, NO code fences, NO comments, NO extra text.

Now analyze the following repository file list and return ONLY the JSON object:

''' + code_context
    
    # Retry loop for JSON parsing errors
    for attempt in range(config.max_json_retries):
        try:
            response = model.generate_content(prompt)
            raw_text = response.text
            
            # Clean markdown if present
            cleaned_text = _clean_json_response(raw_text)
            
            architecture = json.loads(cleaned_text)
            logger.info(f"Architecture analyzed: {architecture.get('system_summary', 'N/A')[:80]}...")
            logger.info(f"Components: {len(architecture.get('components', []))}")
            logger.info(f"Connections: {len(architecture.get('connections', []))}")
            
            # Save to cache
            if cache_path:
                save_architecture_cache(architecture, cache_path)
            
            # Save to persistent repo JSON
            if repo_path:
                save_architecture_json(architecture, repo_path)
            
            return architecture
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON Parse Error (attempt {attempt + 1}/{config.max_json_retries}): {e}")
            logger.debug(f"Raw response (first 500 chars): {raw_text[:500]}")
            
            if attempt < config.max_json_retries - 1:
                # Retry with correction prompt
                logger.info("Retrying with correction prompt...")
                prompt = f"""The previous response was not valid JSON. Please fix it and return ONLY valid JSON with no markdown formatting.

Previous response:
{raw_text[:1000]}

Return the corrected JSON object with the exact structure specified earlier."""
            else:
                logger.error("Failed to parse JSON after all retries")
                return None
                
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            return None
    
    return None


def build_hero_prompt(
    architecture: Dict[str, Any], 
    hero_style: Optional[str] = None,
    config: Optional[RepoArtistConfig] = None
) -> Optional[str]:
    """
    Step 3: Builds the prompt for the image generation model.
    
    Args:
        architecture: Architecture dictionary from analyze_architecture()
        hero_style: Optional style variation to append
        config: Configuration object
        
    Returns:
        Prompt string if successful, None otherwise
    """
    if not architecture:
        return None
    
    if config is None:
        config = RepoArtistConfig.from_env()
    
    logger.info("Step 3: Building hero image prompt...")
    
    system_summary = architecture.get("system_summary", "A software system")
    components = architecture.get("components", [])[:config.max_components]
    connections = architecture.get("connections", [])[:config.max_connections]
    
    # Visual descriptors for different component types
    type_visuals = {
        "frontend": "a floating glass interface screen with UI elements",
        "backend": "a server rack module with data streams",
        "api": "a server rack module with data streams",
        "database": "a cylindrical data storage unit with holographic rings",
        "worker": "a processing core sending signals outward",
        "cli": "a terminal window and code icons",
        "external_service": "an external service tile or cloud endpoint icon",
        "ai_model": "a glowing neural network brain visualization",
        "queue": "a floating data buffer conduit",
        "cache": "a glowing crystal memory bank",
        "storage": "a heavy metallic data vault",
        "other": "a modular tech block"
    }

    # Build component platform descriptions
    platform_lines = []
    for i, comp in enumerate(components, 1):
        label = comp.get("label", f"Component {i}")
        comp_type = comp.get("type", "other").lower()
        role = comp.get("role", "Handles system functionality")
        
        # Use specific visual descriptions if available
        if "visual_3d_object" in comp and "visual_label" in comp:
             platform_lines.append(f"Platform {i}: {comp['visual_3d_object']}. {comp['visual_label']}")
        else:
            visual = type_visuals.get(comp_type, type_visuals["other"])
            platform_lines.append(f'Platform {i} labeled "{label}" (type: {comp_type}) – shows {visual}, representing {role}. Label should be a floating holographic text above the object.')
    
    # Build connection arrow descriptions
    id_to_label = {c["id"]: c["label"] for c in components}
    arrow_lines = []
    for conn in connections:
        from_label = id_to_label.get(conn["from"], conn["from"])
        to_label = id_to_label.get(conn["to"], conn["to"])
        conn_label = conn.get("label", "data flow")
        arrow_lines.append(f'An arrow from "{from_label}" to "{to_label}" labeled "{conn_label}".')
    
    prompt = f"""A high-end sci-fi isometric flow diagram of a {system_summary[:60]}..., with {len(components)} clearly labeled glowing 3D platforms connected by arrows.
    
    System overview: {system_summary}
    
    Platforms (Cyberpunk HUD interface style, flat vector labels overlaying 3D objects):
    {chr(10).join(platform_lines)}
    
    Data flow:
    {chr(10).join(arrow_lines)}
    
    Visual style: professional futuristic dark UI, isometric 3D glass platforms, neon blue and magenta edges, large, crisp English labels on each platform, clear arrows with short labels, wide horizontal layout suitable for a README banner, no random text, no extra shapes, no unreadable scribbles. ensure text labels are described as 'floating UI elements', NOT textures on the object."""
    
    if hero_style:
        prompt += f" {hero_style}"
        logger.info(f"Added style variation: {hero_style}")
    
    logger.info(f"Hero prompt built ({len(prompt)} chars)")
    return prompt


def generate_hero_image_imagen3(
    prompt: str, 
    output_path: Optional[str] = None,
    config: Optional[RepoArtistConfig] = None
) -> Optional[bytes]:
    """
    Step 4 Tier 1: Generates image using Google Imagen 3 (Vertex AI).
    
    Args:
        prompt: Image generation prompt
        output_path: Optional path to save image
        config: Configuration object
        
    Returns:
        Image bytes if successful, None otherwise
    """
    if config is None:
        config = RepoArtistConfig.from_env()
    
    if not config.imagen_project_id:
        logger.info("Imagen 3 not configured (IMAGEN_PROJECT_ID missing), skipping Tier 1")
        return None
    
    logger.info("Step 4 Tier 1: Generating image via Google Imagen 3...")
    
    try:
        from google.cloud import aiplatform
        from vertexai.preview.vision_models import ImageGenerationModel
        
        # Initialize Vertex AI
        aiplatform.init(project=config.imagen_project_id, location=config.imagen_location)
        
        # Load Imagen 3 model
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        
        # Generate image
        logger.debug("Requesting image from Imagen 3...")
        response = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9",
        )
        
        # ImageGenerationResponse has an .images attribute which is a list
        if response and hasattr(response, 'images') and response.images:
            image_bytes = response.images[0]._image_bytes
            
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"Image saved to {output_path}")
            
            return image_bytes
        else:
            logger.warning("Imagen 3 returned no images")
            return None
            
    except ImportError:
        logger.warning("google-cloud-aiplatform not installed, skipping Imagen 3")
        return None
    except Exception as e:
        logger.warning(f"Imagen 3 error: {e}, falling back to Tier 2")
        return None


def generate_hero_image_pollinations(
    prompt: str, 
    output_path: Optional[str] = None
) -> Optional[bytes]:
    """
    Step 4 Tier 2: Generates image using Pollinations.ai free API.
    
    Args:
        prompt: Image generation prompt
        output_path: Optional path to save image
        
    Returns:
        Image bytes if successful, None otherwise
    """
    logger.info("Step 4 Tier 2: Generating image via Pollinations.ai...")
    
    # Enrich prompt for text legibility
    enhanced_prompt = prompt + " . perfect typography, sharp text, legible labels, high contrast text, white font, no spelling errors, text floating in front"
    
    encoded_prompt = urllib.parse.quote(enhanced_prompt, safe='')
    url = POLLINATIONS_URL.format(prompt=encoded_prompt) + "?width=1280&height=720&model=flux&enhance=true"
    
    logger.debug("Requesting image from Pollinations...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=120)
            
            if response.status_code == 200:
                if output_path:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Image saved to {output_path}")
                return response.content
            
            elif response.status_code in [502, 503, 504]:
                logger.warning(f"Pollinations server busy (HTTP {response.status_code}). Retrying ({attempt + 1}/{max_retries})...")
                time.sleep(1.5)
                continue
            
            else:
                logger.error(f"Pollinations error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
            time.sleep(1)
            
    logger.error("Failed to generate image from Pollinations after retries")
    return None


def architecture_to_mermaid(architecture: Dict[str, Any]) -> Optional[str]:
    """
    Converts JSON architecture to Mermaid flowchart code.
    
    Args:
        architecture: Architecture dictionary
        
    Returns:
        Mermaid code string if successful, None otherwise
    """
    if not architecture:
        return None
    
    lines = ["graph LR"]
    
    def sanitize_id(id_str: str) -> str:
        return ''.join(c for c in id_str if c.isalnum())
    
    id_map = {}
    for comp in architecture.get("components", []):
        original_id = comp["id"]
        id_map[original_id] = sanitize_id(original_id)
    
    for comp in architecture.get("components", []):
        comp_id = sanitize_id(comp["id"])
        label = comp["label"].replace('"', '').replace('[', '').replace(']', '')
        lines.append(f"    {comp_id}({label})")
    
    lines.append("")
    
    for conn in architecture.get("connections", []):
        from_id = id_map.get(conn["from"], sanitize_id(conn["from"]))
        to_id = id_map.get(conn["to"], sanitize_id(conn["to"]))
        lines.append(f"    {from_id} --> {to_id}")
    
    return "\n".join(lines)


def generate_hero_image_mermaid(
    architecture: Dict[str, Any], 
    output_path: Optional[str] = None
) -> Optional[bytes]:
    """
    Step 4 Tier 3: Fallback - generates diagram using mermaid.ink.
    
    Args:
        architecture: Architecture dictionary
        output_path: Optional path to save image
        
    Returns:
        Image bytes if successful, None otherwise
    """
    logger.info("Step 4 Tier 3: Generating diagram via mermaid.ink (fallback)...")
    
    mermaid_code = architecture_to_mermaid(architecture)
    if not mermaid_code:
        return None
    
    logger.debug(f"Mermaid code:\n{mermaid_code}\n")
    
    encoded = base64.b64encode(mermaid_code.encode('utf8')).decode('utf8')
    url = f"https://mermaid.ink/img/{encoded}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Diagram saved to {output_path}")
            return response.content
        else:
            logger.error(f"mermaid.ink error: HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return None


def generate_hero_image(
    prompt: str,
    architecture: Dict[str, Any],
    output_path: Optional[str] = None,
    config: Optional[RepoArtistConfig] = None
) -> Optional[bytes]:
    """
    Generate hero image with multi-tier fallback strategy.
    
    Tier 1: Google Imagen 3 (Premium)
    Tier 2: Pollinations.ai (Free)
    Tier 3: Mermaid Diagram (Fallback)
    
    Args:
        prompt: Image generation prompt
        architecture: Architecture dictionary (for Mermaid fallback)
        output_path: Optional path to save image
        config: Configuration object
        
    Returns:
        Image bytes if successful, None otherwise
    """
    if not prompt:
        logger.error("Empty prompt. Cannot generate image.")
        return None

    # Check for cached image if not forcing re-analysis
    if config and not config.force_reanalyze and output_path and os.path.exists(output_path):
        logger.info(f"Using cached hero image at {output_path}")
        try:
            with open(output_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read cached image: {e}. Regenerating.")

    # Try Tier 1: Imagen 3
    result = generate_hero_image_imagen3(prompt, output_path, config)
    if result:
        return result
    
    # Try Tier 2: Pollinations
    result = generate_hero_image_pollinations(prompt, output_path)
    if result:
        return result
    
    # Fallback to Tier 3: Mermaid
    logger.warning("All image generation tiers failed, falling back to Mermaid diagram")
    return generate_hero_image_mermaid(architecture, output_path)


def update_readme_content(
    original_content: str, 
    image_url: str = "./assets/architecture_diagram.png"
) -> str:
    """
    Step 5: Returns the updated README content as a string.
    Does NOT write to file.
    
    Args:
        original_content: Original README content
        image_url: Path/URL to architecture image
        
    Returns:
        Updated README content
    """
    logger.info("Step 5: Preparing README update...")
    
    # Ensure explicit relative path for GitHub compatibility
    if not image_url.startswith("http") and not image_url.startswith("./") and not image_url.startswith("/"):
        image_url = f"./{image_url}"
        
    image_line = f"![Architecture]({image_url})"
    
    if not original_content:
        # Create new content if empty
        return f"# Project\n\n{image_line}\n"
    
    # Check if image already exists (update it)
    escaped_filename = re.escape(os.path.basename(image_url))
    # Match ![...](...filename...) but be careful not to match inside code blocks if possible
    # For now, regex replacement is standard behavior
    pattern = r'!\[.*?\]\(.*' + escaped_filename + r'\)'

    if re.search(pattern, original_content):
        new_content = re.sub(pattern, image_line, original_content)
        logger.info("Updated existing architecture image reference")
        return new_content
    
    # Insert Logic - Improved to avoid code blocks
    lines = original_content.split('\n')
    insert_index = 0
    found_title = False
    
    # Strategy: Insert immediately after the first top-level header (# Title)
    for i, line in enumerate(lines):
        if line.strip().startswith('# '):
            found_title = True
            # Insert after the title line
            insert_index = i + 1
            break
            
    if not found_title:
        # No title found, insert at very top
        insert_index = 0
    
    # Insert with proper spacing
    # We add the image and ensure there are blank lines around it
    lines.insert(insert_index, '')
    lines.insert(insert_index + 1, image_line)
    lines.insert(insert_index + 2, '')
    
    logger.info("Added hero image reference to README")
    return '\n'.join(lines)
