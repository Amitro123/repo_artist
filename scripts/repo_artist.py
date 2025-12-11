import os
import requests
import io
from PIL import Image
import google.generativeai as genai
from pathlib import Path
import time
import urllib.parse
import random

# --- CONFIGURATION ---
# Using Pollinations/Flux - Strong model for composition
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"

# Expanded style to allow a full scene, not just a single icon
STYLE_TEMPLATE = """
Isometric 3D technical architecture visualization, dark mode, neon tech aesthetic. 
Floating glass and crystal modules connected by glowing data streams. 
Octane render, unreal engine 5, hyper-realistic, 8k, volumetric lighting. 
Clean composition, translucent frosted glass materials.
Scene description:
"""

def get_code_context(root_dir="."):
    """Harvests file names to understand the tech stack structure."""
    file_list = []
    # More aggressive filtering to focus on main files
    ignore_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'assets', '.github', '.idea', 'tests', 'docs'}
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            # Focus on core code and config files
            if file.endswith(('.py', '.js', '.ts', '.tsx', '.go', '.rs', 'Dockerfile', 'docker-compose.yml')):
                # Keep folder name for context (e.g. backend/main.py)
                path = os.path.relpath(os.path.join(root, file), root_dir)
                file_list.append(path)
    
    # Take top 40 files that aren't too deep
    return ", ".join(sorted(file_list)[:40])

def analyze_and_prompt(code_context):
    print("🧠 Analyzing Architecture structure with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ Missing GEMINI_API_KEY. Using default.")
        return "A central computing core connected to floating data modules."

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # Using 2.5-flash as 1.5 is deprecated
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    # --- Major Change Here ---
    # Asking Gemini to analyze structure and describe a composition
    instruction = f"""
    You are a Technical Artist. Analyze these project filenames to understand the software architecture.
    
    Your task: Create a visual description of 3-4 interconnected 3D glass modules representing the key parts of this system.
    
    Rules:
    1. Identify key components (e.g., "Backend API", "Frontend App", "Database", "AI Worker", "Orchestrator").
    2. Describe them as glowing glass/crystal structures.
    3. Describe how they are connected by data pipes.
    4. Keep it abstract but structured. Do NOT ask for specific text labels.
    
    Example Output for a Fullstack app: 
    "A central glowing cubic server block connected via blue pipes to a floating glass interface panel on the left, and a cylindrical crystal database unit on the right."
    
    Filenames context: {code_context}
    
    Output ONLY the visual description sentence.
    """
    
    try:
        response = model.generate_content(instruction)
        visual_idea = response.text.strip()
        print(f"💡 Gemini Structural Concept: {visual_idea}")
        return visual_idea
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return "A central glowing computing core connected to multiple satellite data modules."

def generate_image_pollinations(visual_description):
    print(f"🎨 Generating Structural Image via Pollinations (Flux)...")
    
    full_prompt = f"{STYLE_TEMPLATE} {visual_description}"
    
    # Added random seed for variety and enhance=true for quality
    seed = random.randint(0, 100000)
    
    encoded_prompt = urllib.parse.quote(full_prompt)
    url = f"{POLLINATIONS_URL}{encoded_prompt}?width=1280&height=720&nologo=true&model=flux&enhance=true&seed={seed}"
    
    print(f"🔗 Calling URL length: {len(url)}")

    try:
        response = requests.get(url, timeout=45) # Extended timeout slightly
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"❌ Error from Pollinations: {response.status_code} - {response.text}")
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
    code_ctx = get_code_context()
    print(f"📂 Context sent to AI: {code_ctx[:200]}...") # Debug print
    scene_desc = analyze_and_prompt(code_ctx)
    img_bytes = generate_image_pollinations(scene_desc)
    save_image(img_bytes)
