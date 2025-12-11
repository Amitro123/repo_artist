import os
import requests
import base64
import google.generativeai as genai
from pathlib import Path

# --- CONFIGURATION ---
KROKI_ENDPOINT = "https://kroki.io/mermaid/png"

def get_code_context(root_dir="."):
    """Harvests file structure."""
    structure = []
    ignore_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'assets', '.github', '.idea', 'tests'}
    important_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.md', '.yml', 'Dockerfile'}
    
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
            if Path(file).suffix in important_extensions:
                structure.append(f"{indent}  📄 {file}")
                
    return "\n".join(structure)

def generate_mermaid_code(code_context):
    """Generates CLEAN Mermaid code via Gemini."""
    print("🧠 Analyzing architecture with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY missing.")
        return None

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # Auto-corrected to 2.5-flash-lite to avoid deprecation errors
    model = genai.GenerativeModel('gemini-2.5-flash-lite') 
    
    instruction = f"""
    You are a Senior Software Architect.
    Analyze this file structure and generate a Mermaid.js flowchart (graph TD).
    
    Rules:
    1. Start immediately with 'graph TD'.
    2. Define nodes with clear IDs and Labels (e.g., A[Client] --> B[Server]).
    3. Do NOT use special characters inside labels that might break syntax.
    4. Group related files using subgraphs (subgraph Backend ... end).
    5. Output ONLY the raw code. NO markdown backticks (```). NO explanations.
    
    File Structure:
    {code_context}
    """
    
    try:
        response = model.generate_content(instruction)
        mermaid_code = response.text.strip()
        
        # --- Aggressive Markdown Cleaning ---
        # Remove all possible markdown wrappers
        mermaid_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
        
        # Ensure it starts with 'graph ' (sometimes Gemini adds preamble)
        if "graph " not in mermaid_code:
            mermaid_code = "graph TD\n" + mermaid_code
            
        print(f"💡 Generated Mermaid Code:\n{mermaid_code}\n")
        return mermaid_code
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return None

def render_diagram_kroki(mermaid_code, output_path="assets/architecture_diagram.png"):
    """Renders the diagram via Kroki."""
    if not mermaid_code: return

    print(f"🎨 Rendering diagram via Kroki...")
    
    try:
        # Base64 Encode (URL Safe)
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
            # Ensure helpful debug info is printed
            print(f"Try debugging here: https://kroki.io/mermaid/svg/{encoded_code}")

    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    structure = get_code_context()
    mermaid_code = generate_mermaid_code(structure)
    render_diagram_kroki(mermaid_code)
