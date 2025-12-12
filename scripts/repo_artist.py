#!/usr/bin/env python3
"""
Repo-Artist: Architecture Hero Image Generator

Analyzes a Git repository and generates a sci-fi isometric architecture
hero image that is automatically added to the repo's README.

Pipeline:
1. Harvest repository file structure
2. Analyze with Gemini → JSON architecture (with caching)
3. Build image prompt from architecture
4. Generate PNG via HTTP image API (with caching)
5. Update README with hero image reference

Usage:
    python scripts/repo_artist.py [--mode image|mermaid] [--root DIR]
    python scripts/repo_artist.py --refresh-architecture    # Force new LLM analysis
    python scripts/repo_artist.py --force-image             # Regenerate image
    python scripts/repo_artist.py --hero-style "more neon"  # Custom style variation

Environment Variables:
    GEMINI_API_KEY      - Required for architecture analysis
    ARCH_MODEL_NAME     - LLM model to use (default: gemini-2.5-flash)
"""

import os
import re
import sys
import json
import argparse
import requests
import urllib.parse
import base64
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
OUTPUT_PATH = "assets/architecture_diagram.png"
ARCHITECTURE_CACHE_PATH = "assets/architecture.json"
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
MERMAID_INK_URL = "https://mermaid.ink/img/{encoded}"

# Default model - can be overridden via ARCH_MODEL_NAME env var
DEFAULT_MODEL = "gemini-2.5-flash"


def get_code_context(root_dir="."):
    """Step 1: Harvests file structure from the repository."""
    structure = []
    ignore_dirs = {
        '.git', 'node_modules', 'venv', '.venv', '__pycache__', 
        'assets', '.github', '.idea', 'tests', 'dist', 'build',
        'coverage', '.pytest_cache', '.mypy_cache', '.tox', 'eggs'
    }
    important_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.rb',
        '.json', '.md', '.yml', '.yaml', '.toml', '.sql', '.sh', '.dockerfile'
    }
    important_files = {
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        'Makefile', 'requirements.txt', 'package.json', 'Cargo.toml',
        'go.mod', 'pom.xml', 'build.gradle'
    }
    
    print("📂 Step 1: Harvesting project structure...")
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        depth = root.count(os.sep) - root_dir.count(os.sep)
        if depth > 3:
            continue
            
        indent = "  " * depth
        folder_name = os.path.basename(root)
        if folder_name and folder_name != ".":
            structure.append(f"{indent}📁 {folder_name}/")
        
        for file in files:
            file_lower = file.lower()
            if Path(file).suffix.lower() in important_extensions or file in important_files or file_lower in important_files:
                structure.append(f"{indent}  📄 {file}")
                
    result = "\n".join(structure)
    print(f"   Found {len(structure)} items")
    return result


def load_cached_architecture(cache_path=ARCHITECTURE_CACHE_PATH):
    """Loads architecture from cache file if it exists."""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                architecture = json.load(f)
            print(f"📦 Loaded cached architecture from {cache_path}")
            print(f"   Components: {len(architecture.get('components', []))}")
            return architecture
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ Failed to load cache: {e}")
    return None


def save_architecture_cache(architecture, cache_path=ARCHITECTURE_CACHE_PATH):
    """Saves architecture JSON to cache file."""
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(architecture, f, indent=2)
        print(f"💾 Architecture cached to {cache_path}")
        return True
    except IOError as e:
        print(f"⚠️ Failed to save cache: {e}")
        return False


def analyze_architecture(code_context, force_refresh=False, cache_path=ARCHITECTURE_CACHE_PATH):
    """
    Step 2: Analyzes code structure and returns JSON architecture via Gemini.
    
    Args:
        code_context: File structure string
        force_refresh: If True, skip cache and call LLM
        cache_path: Path to architecture cache file
    """
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = load_cached_architecture(cache_path)
        if cached:
            return cached
    
    print("🧠 Step 2: Analyzing architecture with Gemini...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not set.")
        return None

    # Use configurable model name
    model_name = os.getenv("ARCH_MODEL_NAME", DEFAULT_MODEL)
    print(f"   Using model: {model_name}")
    
    genai.configure(api_key=api_key)
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
      "role": "1 sentence describing what this component does"
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
- Use ONLY component IDs that appear in "components".
- Prefer 3–7 components; merge minor pieces into larger logical units.
- Infer common patterns (frontend, backend/api, database, workers, external APIs, AI models, etc.).
- The response MUST be raw JSON: NO markdown, NO code fences, NO comments, NO extra text.

Now analyze the following repository file list and return ONLY the JSON object:

''' + code_context
    
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Clean markdown if present
        if raw_text.startswith("```"):
            parts = raw_text.split("```")
            if len(parts) >= 2:
                raw_text = parts[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()
        
        architecture = json.loads(raw_text)
        print(f"✅ Architecture analyzed: {architecture.get('system_summary', 'N/A')[:80]}...")
        print(f"   Components: {len(architecture.get('components', []))}")
        print(f"   Connections: {len(architecture.get('connections', []))}")
        
        # Save to cache
        save_architecture_cache(architecture, cache_path)
        
        return architecture
        
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON Parse Error: {e}")
        print(f"   Raw response (first 500 chars): {raw_text[:500]}")
        return None
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return None


def build_hero_prompt(architecture, hero_style=None):
    """
    Step 3: Takes the JSON from analyze_architecture() and returns a single text prompt
    following the hero image style template.
    
    Args:
        architecture: JSON architecture dict
        hero_style: Optional style variation string to append
    """
    if not architecture:
        return None
    
    print("🎨 Step 3: Building hero image prompt...")
    
    system_summary = architecture.get("system_summary", "A software system")
    components = architecture.get("components", [])[:7]
    connections = architecture.get("connections", [])[:7]
    
    # Build component platform descriptions
    platform_lines = []
    for i, comp in enumerate(components, 1):
        label = comp.get("label", f"Component {i}")
        comp_type = comp.get("type", "other")
        role = comp.get("role", "Handles system functionality")
        platform_lines.append(f'Platform {i}: Label "{label}". Type: {comp_type}. Role: {role}')
    
    # Build connection arrow descriptions
    id_to_label = {c["id"]: c["label"] for c in components}
    arrow_lines = []
    for conn in connections:
        from_label = id_to_label.get(conn["from"], conn["from"])
        to_label = id_to_label.get(conn["to"], conn["to"])
        conn_label = conn.get("label", "data flow")
        arrow_lines.append(f'Arrow from "{from_label}" to "{to_label}": "{conn_label}"')
    
    # Compose full prompt using exact style template
    prompt = f"""A high-end sci-fi isometric illustration of a software architecture, showing {len(components)} floating 3D platforms connected by glowing arrows.

System overview: {system_summary}

Components as floating platforms:
{chr(10).join(platform_lines)}

Data flows between platforms:
{chr(10).join(arrow_lines)}

Visual style requirements:
- Professional futuristic dark UI background with deep blue/purple tones
- Isometric 3D perspective with floating glass/metallic platforms
- Neon blue and magenta accent lighting with subtle glow effects
- Clear, readable English labels on or near each platform
- Glowing directional arrows showing data/control flow between components
- Wide horizontal banner composition (16:9 aspect ratio)
- Clean and non-cartoonish, suitable as a GitHub README hero image
- No random abstract shapes, crystals, or unrelated elements"""
    
    # Append custom style variation if provided
    if hero_style:
        prompt += f"\n- Additional style: {hero_style}"
        print(f"   Added style variation: {hero_style}")
    
    print(f"✅ Hero prompt built ({len(prompt)} chars)")
    return prompt


# Alias for backward compatibility
build_image_prompt = build_hero_prompt


def generate_hero_image(prompt, output_path="assets/architecture_diagram.png"):
    """
    Calls a low-cost or free HTTP image model (Pollinations.ai)
    with the given prompt and saves the returned PNG to output_path.
    This works in plain GitHub Actions (no Antigravity-only APIs).
    """
    return generate_hero_image_pollinations(prompt, output_path)


def generate_hero_image_pollinations(prompt, output_path):
    """Step 4a: Generates image using Pollinations.ai free API."""
    print("🖼️ Step 4: Generating image via Pollinations.ai...")
    
    # URL-encode the prompt
    encoded_prompt = urllib.parse.quote(prompt, safe='')
    
    # Add parameters for better quality
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&model=flux"
    
    print(f"   Requesting image from Pollinations...")
    
    try:
        response = requests.get(url, timeout=120)
        
        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ Image saved to {output_path} ({len(response.content) // 1024} KB)")
            return True
        else:
            print(f"❌ Pollinations error: HTTP {response.status_code}")
            return False
            
    except requests.Timeout:
        print("❌ Pollinations timeout (image generation took too long)")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def architecture_to_mermaid(architecture):
    """Converts JSON architecture to Mermaid flowchart code."""
    if not architecture:
        return None
    
    lines = ["graph LR"]
    
    def sanitize_id(id_str):
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


def generate_hero_image_mermaid(architecture, output_path):
    """Step 4b: Fallback - generates diagram using mermaid.ink."""
    print("🖼️ Step 4: Generating diagram via mermaid.ink (fallback)...")
    
    mermaid_code = architecture_to_mermaid(architecture)
    if not mermaid_code:
        return False
    
    print(f"   Mermaid code:\n{mermaid_code}\n")
    
    encoded = base64.b64encode(mermaid_code.encode('utf8')).decode('utf8')
    url = f"https://mermaid.ink/img/{encoded}"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ Diagram saved to {output_path}")
            return True
        else:
            print(f"❌ mermaid.ink error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def update_readme(image_path="assets/architecture_diagram.png", readme_path="README.md"):
    """Step 5: Ensures README.md contains a reference to the hero image."""
    print("📝 Step 5: Updating README.md...")
    
    image_line = f"![Architecture]({image_path})"
    
    if not os.path.exists(readme_path):
        print(f"   README.md not found, creating new one...")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(f"# Project\n\n{image_line}\n")
        print(f"✅ Created README.md with hero image")
        return True
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if image_line in content:
        print("   README already contains hero image reference")
        return True
    
    pattern = r'!\[.*?\]\(assets/architecture_diagram\.png\)'
    if re.search(pattern, content):
        content = re.sub(pattern, image_line, content)
        print("   Updated existing architecture image reference")
    else:
        lines = content.split('\n')
        insert_index = 0
        
        for i, line in enumerate(lines):
            if line.startswith('#'):
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip() == '':
                        insert_index = j + 1
                        break
                    elif not lines[j].startswith('#') and lines[j].strip():
                        insert_index = j + 1
                break
        
        if insert_index == 0:
            insert_index = 2
        
        lines.insert(insert_index, '')
        lines.insert(insert_index + 1, image_line)
        lines.insert(insert_index + 2, '')
        content = '\n'.join(lines)
        print("   Added hero image reference to README")
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ README.md updated")
    return True


def main():
    """Main pipeline execution."""
    parser = argparse.ArgumentParser(
        description="Repo-Artist: Generate architecture hero images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/repo_artist.py                         # Use cached architecture + image
    python scripts/repo_artist.py --refresh-architecture  # Force new LLM analysis
    python scripts/repo_artist.py --force-image           # Regenerate image from cache
    python scripts/repo_artist.py --hero-style "minimal"  # Custom style variation
    python scripts/repo_artist.py --mode mermaid          # Use mermaid diagram fallback

Environment Variables:
    GEMINI_API_KEY      - Required for architecture analysis
    ARCH_MODEL_NAME     - LLM model to use (default: gemini-2.5-flash)
        """
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["image", "mermaid"],
        default="image",
        help="Generation mode: 'image' uses Pollinations.ai, 'mermaid' uses mermaid.ink (default: image)"
    )
    parser.add_argument(
        "--root", "-r",
        default=".",
        help="Root directory of the repository to analyze (default: current directory)"
    )
    parser.add_argument(
        "--output", "-o",
        default=OUTPUT_PATH,
        help=f"Output path for generated image (default: {OUTPUT_PATH})"
    )
    parser.add_argument(
        "--skip-readme",
        action="store_true",
        help="Skip updating README.md"
    )
    parser.add_argument(
        "--refresh-architecture",
        action="store_true",
        help="Force new LLM analysis, ignoring cached architecture"
    )
    parser.add_argument(
        "--force-image",
        action="store_true",
        help="Regenerate hero image even if one already exists"
    )
    parser.add_argument(
        "--hero-style",
        type=str,
        default=None,
        help="Optional style variation to append to image prompt (e.g. 'more minimal', 'more neon')"
    )
    
    args = parser.parse_args()
    
    # Also check environment variable overrides
    refresh_arch = args.refresh_architecture or os.getenv("REFRESH_ARCHITECTURE", "").lower() == "true"
    force_image = args.force_image or os.getenv("FORCE_IMAGE", "").lower() == "true"
    
    print("\n" + "=" * 60)
    print("🚀 Repo-Artist Pipeline Starting...")
    print(f"   Mode: {args.mode}")
    print(f"   Root: {os.path.abspath(args.root)}")
    print(f"   Refresh Architecture: {refresh_arch}")
    print(f"   Force Image: {force_image}")
    if args.hero_style:
        print(f"   Hero Style: {args.hero_style}")
    print("=" * 60 + "\n")
    
    # Check if image already exists and we don't need to regenerate
    if not force_image and os.path.exists(args.output):
        print(f"📦 Image already exists at {args.output}")
        print("   Use --force-image to regenerate")
        
        # Still update README if needed
        if not args.skip_readme:
            update_readme(args.output)
        
        print("\n" + "=" * 60)
        print("✅ Repo-Artist Pipeline Complete (using cached image)")
        print("=" * 60 + "\n")
        return
    
    # Step 1: Harvest repository structure
    structure = get_code_context(args.root)
    if not structure:
        print("❌ No files found to analyze.")
        sys.exit(1)
    
    print()
    
    # Step 2: Analyze architecture with Gemini (with caching)
    architecture = analyze_architecture(structure, force_refresh=refresh_arch)
    if not architecture:
        print("❌ Failed to analyze architecture.")
        sys.exit(1)
    
    print()
    
    # Step 3 & 4: Generate image based on mode
    success = False
    if args.mode == "image":
        prompt = build_hero_prompt(architecture, hero_style=args.hero_style)
        if prompt:
            print()
            success = generate_hero_image_pollinations(prompt, args.output)
            
            # Fallback to mermaid if image generation fails
            if not success:
                print("\n⚠️ Image generation failed, falling back to mermaid mode...")
                success = generate_hero_image_mermaid(architecture, args.output)
    else:
        success = generate_hero_image_mermaid(architecture, args.output)
    
    if not success:
        print("❌ Failed to generate hero image.")
        sys.exit(1)
    
    print()
    
    # Step 5: Update README
    if not args.skip_readme:
        update_readme(args.output)
    
    print()
    print("=" * 60)
    print("✅ Repo-Artist Pipeline Complete!")
    print(f"   Output: {args.output}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
