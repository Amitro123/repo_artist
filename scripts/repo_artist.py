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
# Hero Object Style: Single, High-Impact 3D Element
STYLE_TEMPLATE = """
Hyper-realistic 3D render, dark mode, neon tech aesthetic, isometric view.
Volumetric lighting, octane render, 8k, unreal engine 5, glowing glass and metal textures.
Background is a dark circuit board pattern.
Subject:
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
    Uses Gemini to dynamically decide the visual subject based on the code.
    Instead of a complex flow, it chooses one powerful 'Hero Object'.
    """
    print("🧠 Analyzing code DNA with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        return "A futuristic glowing crystal structure in a dark sci-fi environment."

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # This prompt makes Gemini an Art Director
    instruction = f"""
    Analyze this codebase to understand its function (e.g., is it a Database? CLI tool? Web App? AI Agent?).
    
    Your task: Create a prompt for an Image Generator (Stable Diffusion) to create a "Hero Image" for this repo.
    
    1. Identify the 'Core Concept' (e.g., Automation = Gears, AI = Brain, Web = Interface, Security = Shield).
    2. Describe a SINGLE, high-tech 3D object representing this concept.
    3. Keep it abstract and sci-fi.
    
    Examples:
    - For a CLI Tool: "A glowing futuristic mechanical cyber-hand holding a digital wrench, isometric view."
    - For a Database: "A towering monolith server block glowing with purple data streams, isometric view."
    - For a Web App: "A floating holographic glass interface dashboard in a dark void, isometric view."
    
    Code Context:
    {code_context}
    
    Output ONLY the visual description sentence. Do NOT use words like "diagram" or "flowchart".
    """
    
    try:
        response = model.generate_content(instruction)
        visual_idea = response.text.strip()
        print(f"💡 Gemini Idea: {visual_idea}")
        return visual_idea
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return "A futuristic central server block connected to multiple glowing data nodes."

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
