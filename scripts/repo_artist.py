import os
import requests
import io
from PIL import Image
import google.generativeai as genai
from pathlib import Path
import time
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- CONFIGURATION ---
# Using SDXL Base 1.0 (Free Inference API) - known for great 3D composition
HF_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

# The exact premium 3D prompt structure
# New Style: Clean, Minimalist, Clear
STYLE_TEMPLATE = """
Isometric tech diagram, minimalist vector art style, dark mode.
Glowing neon blue and purple data pipelines connecting nodes.
Clean geometric shapes, professional cloud architecture visualization.
High quality, 4k, schematic design.
"""

def get_code_context(root_dir="."):
    """Harvests code structure for context."""
    context = []
    ignore_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'assets', '.github', '.idea'}
    extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.md', '.yml', '.yaml'}
    
    print("📂 Harvesting code context...")
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if Path(file).suffix in extensions:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(1500) 
                        context.append(f"--- File: {file_path} ---\n{content}\n")
                except Exception:
                    continue
    return "\n".join(context[:10]) 

def analyze_and_prompt(code_context):
    """
    Simplified flow: specific 3-element architecture.
    """
    print("🧠 Defining architecture flow...")
    
    # Specific description for Python/AI projects
    specific_flow = """
    Three main isometric distinct elements connected by glowing tubes:
    1. Left: A floating browser window icon (Client).
    2. Center: A glowing cubic server block (Python Backend).
    3. Right: A crystal brain structure (AI).
    Data flowing from left to right.
    """
    
    return specific_flow

def generate_image_hf(visual_description):
    """Generates image using Hugging Face InferenceClient."""
    from huggingface_hub import InferenceClient
    
    print(f"🎨 Generating image with SDXL via Hugging Face...")
    
    # Combine the style template with the specific flow
    final_prompt = f"{STYLE_TEMPLATE} Scene description: {visual_description}"
    
    if not os.getenv('HF_TOKEN'):
        print("❌ Error: Missing HF_TOKEN")
        return None
    
    try:
        client = InferenceClient(token=os.getenv('HF_TOKEN'))
        
        image = client.text_to_image(
            prompt=final_prompt,
            model=HF_MODEL_ID,
            negative_prompt="text, watermark, low quality, blurry, 2d, flat, drawing, sketch, human, face, deformed",
            num_inference_steps=30,
            guidance_scale=8.0
        )
        
        # Convert PIL Image to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
        
    except Exception as e:
        print(f"❌ Error from HF: {e}")
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
        print(f"❌ Error saving image: {e}")

if __name__ == "__main__":
    if not os.getenv("HF_TOKEN"):
        print("❌ Error: Missing HF_TOKEN environment variable.")
        sys.exit(1)

    code_ctx = get_code_context()
    scene_desc = analyze_and_prompt(code_ctx)
    print(f"\n🧠 GEMINI OUTPUT:\n{scene_desc}\n") 
    img_bytes = generate_image_hf(scene_desc)
    
    if not img_bytes:
        print("❌ Failed to generate image.")
        sys.exit(1)
        
    save_image(img_bytes)
    
    if not os.path.exists("assets/architecture_diagram.png"):
        print("❌ Image file was not saved.")
        sys.exit(1)
