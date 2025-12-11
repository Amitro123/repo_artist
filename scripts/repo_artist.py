import os
import json
import requests
import base64
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
KROKI_ENDPOINT = "https://kroki.io/mermaid/png"

def get_code_context(root_dir="."):
    """Harvests file structure."""
    structure = []
    ignore_dirs = {'.git', 'node_modules', 'venv', '.venv', '__pycache__', 'assets', '.github', '.idea', 'tests', 'dist', 'build'}
    important_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.md', '.yml', '.yaml', 'Dockerfile'}
    
    print("📂 Harvesting project structure...")
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        depth = root.count(os.sep) - root_dir.count(os.sep)
        if depth > 2: continue 
            
        indent = "  " * depth
        folder_name = os.path.basename(root)
        if folder_name and folder_name != ".":
             structure.append(f"{indent}📁 {folder_name}/")
        
        for file in files:
            if Path(file).suffix in important_extensions or file in important_extensions:
                structure.append(f"{indent}  📄 {file}")
                
    return "\n".join(structure)

def analyze_architecture(code_context):
    """Analyzes code structure and returns JSON architecture via Gemini."""
    print("🧠 Analyzing architecture with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY missing.")
        return None

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash-lite') 
    
    prompt = '''You are a senior software architect.

You receive a list of files and folders from an arbitrary Git repository.
From this list, infer the HIGH-LEVEL SOFTWARE ARCHITECTURE of the project.

Your ONLY job is to return a STRICTLY VALID JSON OBJECT with this exact structure:

{
  "system_summary": "short 1–2 sentence English description of what this system does",
  "components": [
    {
      "id": "short_alphanumeric_id",
      "label": "Human readable name of the component",
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
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()
        
        architecture = json.loads(raw_text)
        print(f"✅ Architecture analyzed: {architecture.get('system_summary', 'N/A')}")
        print(f"   Components: {len(architecture.get('components', []))}")
        print(f"   Connections: {len(architecture.get('connections', []))}")
        return architecture
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON Parse Error: {e}")
        print(f"   Raw response: {raw_text[:500]}...")
        return None
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return None

def architecture_to_mermaid(architecture):
    """Converts JSON architecture to Mermaid flowchart code."""
    if not architecture:
        return None
    
    print("🔄 Converting architecture to Mermaid...")
    
    lines = ["graph LR"]
    
    # Sanitize IDs (remove underscores, spaces, special chars)
    def sanitize_id(id_str):
        return ''.join(c for c in id_str if c.isalnum())
    
    # Build ID mapping for connections
    id_map = {}
    for comp in architecture.get("components", []):
        original_id = comp["id"]
        id_map[original_id] = sanitize_id(original_id)
    
    # Add nodes with simplified labels (no brackets or quotes)
    for comp in architecture.get("components", []):
        comp_id = sanitize_id(comp["id"])
        # Keep label simple with only safe characters
        label = comp["label"].replace('"', '').replace('[', '').replace(']', '')
        lines.append(f"    {comp_id}({label})")
    
    lines.append("")
    
    # Add connections (use simple arrows without labels for better compatibility)
    for conn in architecture.get("connections", []):
        from_id = id_map.get(conn["from"], sanitize_id(conn["from"]))
        to_id = id_map.get(conn["to"], sanitize_id(conn["to"]))
        # Simple arrows without labels for maximum Kroki compatibility
        lines.append(f'    {from_id} --> {to_id}')
    
    mermaid_code = "\n".join(lines)
    print(f"💡 Generated Mermaid Code:\n{mermaid_code}\n")
    return mermaid_code

def render_diagram_mermaid(mermaid_code, output_path="assets/architecture_diagram.png"):
    """Renders the diagram via mermaid.ink."""
    if not mermaid_code: return False

    print(f"🎨 Rendering diagram via mermaid.ink...")
    
    try:
        # Base64 Encode (standard, not URL-safe)
        encoded_code = base64.b64encode(mermaid_code.encode('utf8')).decode('utf8')
        url = f"https://mermaid.ink/img/{encoded_code}"

        response = requests.get(url)
        
        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ Diagram saved successfully to {output_path}!")
            return True
        else:
            print(f"❌ Error from mermaid.ink: {response.status_code}")
            print(f"Try debugging here: https://mermaid.ink/img/{encoded_code}")
            return False

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    # Step 1: Get file structure
    structure = get_code_context()
    
    # Step 2: Analyze architecture with Gemini (returns JSON)
    architecture = analyze_architecture(structure)
    
    # Step 3: Convert to Mermaid
    mermaid_code = architecture_to_mermaid(architecture)
    
    # Step 4: Render via mermaid.ink
    render_diagram_mermaid(mermaid_code)
