import os
import requests
import io
from PIL import Image
import google.generativeai as genai
from pathlib import Path
import time
import urllib.parse

# --- CONFIGURATION ---
# Pollinations.ai is a free, public API. No token required.
# We add 'model=flux' to the seed or prompt hints to encourage high quality.
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"

# Style Template optimized for Flux/Pollinations
STYLE_TEMPLATE = """
isometric 3d glass icon, floating in void, dark mode, neon lighting, 
octane render, unreal engine 5, hyper-realistic, 8k, 
glowing edges, translucent frosted glass, minimal tech aesthetic. 
centered composition.
"""

def get_code_context(root_dir="."):
    """Harvests file names to understand the tech stack."""
    file_list = []
    ignore = {'.git', 'node_modules', 'venv', '__pycache__', 'assets', '.github', '.idea'}
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore]
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.md', '.yml', '.json')):
                file_list.append(file)
    
    # Return top 50 files to give context
    return ", ".join(file_list[:50])

def analyze_and_prompt(code_context):
    print("🧠 Analyzing Code DNA with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ Missing GEMINI_API_KEY. Using default.")
        return "A glowing geometric crystal structure"

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    instruction = f"""
    Analyze these filenames to understand the project type.
    Choose ONE single physical object to represent it as a 3D Glass Icon.
    
    - If Automation/Bot -> "A futuristic glass gear mechanism"
    - If AI/LLM -> "A glowing neural network sphere"
    - If Web/Frontend -> "A floating isometric glass interface"
    - If Backend/DB -> "A cubic server block with glowing pipes"
    - If CLI/Tool -> "A holographic command terminal"
    
    Filenames: {code_context}
    
    Output ONLY the object description. Keep it short (3-5 words).
    """
    
    try:
        response = model.generate_content(instruction)
        visual_idea = response.text.strip()
        print(f"💡 Gemini Idea: {visual_idea}")
        return visual_idea
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return "A glowing glass cube"

def generate_image_pollinations(visual_description):
    print(f"🎨 Generating Image via Pollinations.ai (Flux)...")
    
    # Construct the final prompt
    full_prompt = f"{STYLE_TEMPLATE} {visual_description}"
    
    # URL Encode the prompt
    encoded_prompt = urllib.parse.quote(full_prompt)
    
    # Construct URL with parameters (width, height, seed, etc.)
    # nologo=true tries to hide the watermark
    url = f"{POLLINATIONS_URL}{encoded_prompt}?width=1280&height=720&nologo=true&model=flux"
    
    print(f"🔗 Calling URL: {url[:100]}...")

    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"❌ Error from Pollinations: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def save_image(image_bytes, output_path="assets/architecture_diagram.png"):
    if not image_bytes:
        return

    print(f"💾 Saving to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.save(output_path)
        print("✅ Image saved successfully!")
    except Exception as e:
        print(f"❌ Save Error: {e}")

if __name__ == "__main__":
    # Note: HF_TOKEN is NO LONGER REQUIRED. Only Gemini is needed.
    code_ctx = get_code_context()
    scene_desc = analyze_and_prompt(code_ctx)
    img_bytes = generate_image_pollinations(scene_desc)
    save_image(img_bytes)
