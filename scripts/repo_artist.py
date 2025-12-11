import os
import requests
import base64
import google.generativeai as genai
from pathlib import Path

# --- CONFIGURATION ---
# Kroki is a free service that converts code to diagrams
KROKI_ENDPOINT = "https://kroki.io/mermaid/png"

def get_code_context(root_dir="."):
    """Harvests folder structure for Gemini architecture understanding."""
    structure = []
    ignore_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'assets', '.github', '.idea'}
    important_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.md', '.yml', 'Dockerfile'}
    
    print("📂 Harvesting project structure...")
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        depth = root.count(os.sep) - root_dir.count(os.sep)
        if depth > 2: continue # Don't go too deep
            
        indent = "  " * depth
        folder_name = os.path.basename(root)
        if folder_name and folder_name != ".":
             structure.append(f"{indent}📁 {folder_name}/")
        
        for file in files:
            if Path(file).suffix in important_extensions:
                structure.append(f"{indent}  📄 {file}")
                
    return "\n".join(structure)

def generate_mermaid_code(code_context):
    """Asks Gemini to write the diagram code."""
    print("🧠 Analyzing architecture with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY missing.")
        return None

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # Using 2.5-flash-lite as requested in previous turns
    model = genai.GenerativeModel('gemini-2.5-flash-lite') 
    
    instruction = f"""
    You are a Senior Software Architect.
    Analyze this file structure and generate a Mermaid.js flowchart (graph TD).
    
    Rules:
    1. Identify the main components (Frontend, Backend, DB, AI, External APIs).
    2. Draw arrows showing the logical data flow.
    3. Use subgraphs to group related files (e.g. subgraph Backend).
    4. Keep it clean and high-level.
    5. Output ONLY the raw Mermaid code. No markdown formatting.
    
    File Structure:
    {code_context}
    """
    
    try:
        response = model.generate_content(instruction)
        mermaid_code = response.text.strip()
        # Clean up Gemini markdown artifacts
        mermaid_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
        print(f"💡 Generated Mermaid Code:\n{mermaid_code[:100]}...\n")
        return mermaid_code
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return None

def render_diagram_kroki(mermaid_code, output_path="assets/architecture_diagram.png"):
    """Sends code to Kroki and gets an image."""
    if not mermaid_code: return

    print(f"🎨 Rendering diagram via Kroki...")
    
    try:
        # Kroki requires Base64 encoding
        encoded_code = base64.urlsafe_b64encode(mermaid_code.encode('utf8')).decode('utf8')
        url = f"{KROKI_ENDPOINT}/{encoded_code}"

        response = requests.get(url)
        
        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ Diagram saved successfully to {output_path}!")
        else:
            print(f"❌ Error from Kroki: {response.status_code}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    structure = get_code_context()
    mermaid_code = generate_mermaid_code(structure)
    render_diagram_kroki(mermaid_code)
