import os
import glob
import sys
import google.generativeai as genai
import replicate

# --- Configuration ---
# You can also load these from .env if running locally
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

STYLE_TEMPLATE = """
A hyper-realistic, premium 3D technical architecture visualization in an isometric view. The aesthetic is dark mode sci-fi, glowing with neon energy. The color palette features a distinct transition from electric cyan and neon blue (for inputs/sources) to deep neon purple and magenta (for processing/destinations). The environment is a reflective, futuristic circuit board platform floating in a dark data nebula. Key elements are not just icons, but complex, glowing 3D structures encased in glass and energy fields, casting volumetric light onto the platform. Connections are thick, translucent, volumetric data conduits (pipes) with visible pulses of light and data packets moving through them, showing real depth. Floating, glowing futuristic text labels with leader lines point to the elements. The overall feel is high-end CGI, with intense bloom, subsurface scattering, and realistic reflections. [INSERT_FLOW_HERE]
"""

# Supported file extensions for analysis
EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.md', '.json', '.go', '.rs', '.java', '.c', '.cpp', '.h'}

def harvest_code(root_dir="."):
    """Walks through the directory and gathers code context."""
    print(f"Harvesting code from {root_dir}...")
    code_summary = []
    
    for root, dirs, files in os.walk(root_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'venv', 'env', 'dist', 'build', 'assets']]
        
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in EXTENSIONS:
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Limit content per file to avoid huge payloads (basic heuristic)
                        if len(content) > 10000:
                            content = content[:10000] + "\n...[TRUNCATED]"
                        
                        code_summary.append(f"--- FILE: {path} ---\n{content}\n")
                except Exception as e:
                    print(f"Skipping {path}: {e}")
                    
    return "\n".join(code_summary)

def analyze_and_construct_prompt(code_context):
    """Uses Gemini to analyze code and create the prompt."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found.")
        sys.exit(1)
        
    print("Analyzing code with Gemini...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    gemini_prompt = f"""
    Analyze the following codebase and describe its architecture as a visual flow.
    
    Your task is to write ONLY the specific flow description that replaces `[INSERT_FLOW_HERE]` in the style template below.
    Describe the specific nodes (e.g., 'A glass cube labeled FastAPI connected to a glowing Postgres sphere') based on the actual tech stack found.
    Focus on the main components and how they connect.
    
    Codebase Context:
    {code_context[:50000]} # sending first 50k chars to stay safe, though 1.5 flash has huge context.
    
    Output ONLY the description string to be inserted.
    """
    
    response = model.generate_content(gemini_prompt)
    if not response.text:
        print("Error: Gemini returned empty response.")
        sys.exit(1)
        
    flow_description = response.text.strip()
    print(f"Gemini suggested flow: {flow_description}")
    
    final_prompt = STYLE_TEMPLATE.replace("[INSERT_FLOW_HERE]", flow_description)
    return final_prompt.strip()

def generate_image(prompt):
    """Generates image using Replicate Flux.1 Schnell."""
    if not REPLICATE_API_TOKEN:
        print("Error: REPLICATE_API_TOKEN not found.")
        sys.exit(1)
        
    print("Generating image with Replicate (black-forest-labs/flux-schnell)...")
    
    try:
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "go_fast": True,
                "megapixels": "1"
            }
        )
        # Output is usually a list of file objects or URLs
        if output:
            return output[0] # Assuming first item is the image URL/Stream
    except Exception as e:
        print(f"Error generating image: {e}")
        sys.exit(1)
        
    return None

def save_image(image_url_or_stream):
    """Saves the image to assets/architecture_diagram.png."""
    import requests
    from PIL import Image
    from io import BytesIO
    
    if not os.path.exists('assets'):
        os.makedirs('assets')
        
    output_path = os.path.join('assets', 'architecture_diagram.png')
    
    print(f"Saving image to {output_path}...")
    
    try:
        # Check if it's a URL (string) or a FileOutput object
        url = str(image_url_or_stream)
        
        response = requests.get(url)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print("Image saved successfully.")
        else:
            print("Failed to download image.")
    except Exception as e:
        print(f"Error saving image: {e}")

def main():
    print("Starting Repo-Artist...")
    
    # 1. Harvest
    code_context = harvest_code(".")
    if not code_context:
        print("No code found to analyze.")
        sys.exit(0)
        
    # 2. Analyze
    final_prompt = analyze_and_construct_prompt(code_context)
    print("Final Prompt Constructed.")
    
    # 3. Generate
    image_result = generate_image(final_prompt)
    
    # 4. Save
    if image_result:
        save_image(image_result)
    else:
        print("Failed to generate image.")

if __name__ == "__main__":
    main()
