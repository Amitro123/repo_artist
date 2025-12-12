"""
Repo-Artist Core Logic

Contains the pure business logic for harvesting, analysis, and generation.
"""

import os
import re
import json
import urllib.parse
import base64
import google.generativeai as genai
import requests
import time
from pathlib import Path

# --- CONFIGURATION ---
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
MERMAID_INK_URL = "https://mermaid.ink/img/{encoded}"
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
    
    print(f"📂 Step 1: Harvesting project structure from {root_dir}...")
    
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


def load_cached_architecture(cache_path):
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


def save_architecture_cache(architecture, cache_path):
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


def analyze_architecture(code_context, api_key, model_name=DEFAULT_MODEL, force_refresh=False, cache_path=None):
    """
    Step 2: Analyzes code structure and returns JSON architecture via Gemini.
    """
    # Check cache first (unless force refresh)
    if not force_refresh and cache_path:
        cached = load_cached_architecture(cache_path)
        if cached:
            return cached
    
    print("🧠 Step 2: Analyzing architecture with Gemini...")
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not provided.")
        return None

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
        if cache_path:
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
    """Step 3: Builds the prompt for the image generation model."""
    if not architecture:
        return None
    
    print("🎨 Step 3: Building hero image prompt...")
    
    system_summary = architecture.get("system_summary", "A software system")
    components = architecture.get("components", [])[:7]
    connections = architecture.get("connections", [])[:7]
    
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
        
        visual = type_visuals.get(comp_type, type_visuals["other"])
        platform_lines.append(f'Platform {i} labeled "{label}" (type: {comp_type}) – shows {visual}, representing {role}.')
    
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

Platforms:
{chr(10).join(platform_lines)}

Data flow:
{chr(10).join(arrow_lines)}

Visual style: professional futuristic dark UI, isometric 3D glass platforms, neon blue and magenta edges, large, crisp English labels on each platform, clear arrows with short labels, wide horizontal layout suitable for a README banner, no random text, no extra shapes, no unreadable scribbles."""
    
    if hero_style:
        prompt += f" {hero_style}"
        print(f"   Added style variation: {hero_style}")
    
    print(f"✅ Hero prompt built ({len(prompt)} chars)")
    return prompt


def generate_hero_image_pollinations(prompt, output_path=None):
    """Step 4a: Generates image using Pollinations.ai free API."""
    print("🖼️ Step 4: Generating image via Pollinations.ai...")
    
    encoded_prompt = urllib.parse.quote(prompt, safe='')
    url = POLLINATIONS_URL.format(prompt=encoded_prompt) + "?width=1280&height=720&model=flux"
    
    print(f"   Requesting image from Pollinations...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=120)
            
            if response.status_code == 200:
                if output_path:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    print(f"✅ Image saved to {output_path}")
                return response.content
            
            elif response.status_code in [502, 503, 504]:
                print(f"⚠️ Pollinations server busy (HTTP {response.status_code}). Retrying ({attempt + 1}/{max_retries})...")
                time.sleep(1.5)
                continue
            
            else:
                print(f"❌ Pollinations error: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"⚠️ Connection error (attempt {attempt + 1}): {e}")
            time.sleep(1)
            
    print("❌ Failed to generate image from Pollinations after retries.")
    return None


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


def generate_hero_image_mermaid(architecture, output_path=None):
    """Step 4b: Fallback - generates diagram using mermaid.ink."""
    print("🖼️ Step 4: Generating diagram via mermaid.ink (fallback)...")
    
    mermaid_code = architecture_to_mermaid(architecture)
    if not mermaid_code:
        return None
    
    print(f"   Mermaid code:\n{mermaid_code}\n")
    
    encoded = base64.b64encode(mermaid_code.encode('utf8')).decode('utf8')
    url = f"https://mermaid.ink/img/{encoded}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Diagram saved to {output_path}")
            return response.content
        else:
            print(f"❌ mermaid.ink error: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None


def update_readme_content(original_content, image_url="assets/architecture_diagram.png"):
    """
    Step 5: Returns the updated README content as a string.
    Does NOT write to file.
    """
    print("📝 Step 5: Preparing README update...")
    
    image_line = f"![Architecture]({image_url})"
    
    if not original_content:
        # Create new content if empty
        return f"# Project\n\n{image_line}\n"
    
    if image_line in original_content:
        print("   README already contains hero image reference")
        return original_content
    
    # Regex to find existing architecture image (handling diverse paths/filenames is tricky, assuming standard for now)
    # or just checking if our specific image is there.
    # We will look for a similar pattern to replace, or insert at top.
    
    # Escape special characters in the filename for regex
    escaped_filename = re.escape(os.path.basename(image_url))
    pattern = r'!\[.*?\]\(.*' + escaped_filename + r'\)'

    if re.search(pattern, original_content):
        new_content = re.sub(pattern, image_line, original_content)
        print("   Updated existing architecture image reference")
        return new_content
    
    # Insert Logic
    lines = original_content.split('\n')
    insert_index = 0
    
    # Try to insert after title
    for i, line in enumerate(lines):
        if line.startswith('# '):
            # Found title, look for first empty line after it to insert details
            # But usually we want it prominent, maybe right after title
            # Let's try to put it after the first paragraph or header
             for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip() == '':
                        insert_index = j + 1
                        break
                    elif not lines[j].startswith('#') and lines[j].strip():
                         # Found text, maybe insert after this block?
                         # Let's stick to the previous logic: after first header, before next header or empty space
                        insert_index = j + 1
             break
    
    if insert_index == 0:
         # Fallback: Insert at top if no header found (unlikely) or just after start
         insert_index = 2 if len(lines) >= 2 else len(lines)

    lines.insert(insert_index, '')
    lines.insert(insert_index + 1, image_line)
    lines.insert(insert_index + 2, '')
    
    print("   Added hero image reference to README")
    return '\n'.join(lines)
