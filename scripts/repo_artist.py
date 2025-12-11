import os
import requests
import io
from PIL import Image
import google.generativeai as genai
from pathlib import Path
import time

# --- CONFIGURATION ---
HF_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"

# NEW STYLE: Clean, Glassmorphism, Single Centered Icon
STYLE_TEMPLATE = """
A single high-quality 3D glassmorphism icon floating in the center. 
Dark background, soft studio lighting, neon rim light. 
Frosted glass texture, semi-transparent, glowing edges. 
Minimalist, modern UI design, dribbble style, 8k render. 
Subject:
"""

def get_code_context(root_dir="."):
    """Mock context to force specific outcomes based on repo name/content."""
    file_list = []
    for root, dirs, files in os.walk(root_dir):
        if '.git' in root: continue
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.md')):
                file_list.append(file)
    return ", ".join(file_list[:50])

def analyze_and_prompt(code_context):
    print("🧠 Choosing the Hero Object with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        return "A glowing glass cube with a python logo inside."

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # Using 2.5-flash-lite as requested in previous turn
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    instruction = f"""
    Analyze these filenames to understand the project type.
    Choose ONE single physical object to represent it as a 3D Icon.
    
    - If Automation/Bot -> "A futuristic glass gear" or "A cute robot head"
    - If AI/Brain -> "A glowing crystal brain"
    - If Web/Code -> "A glass isometric bracket symbol"
    - If Security -> "A glass shield with a lock"
    
    Filenames: {code_context}
    
    Output ONLY the object description (e.g., "A glowing glass gear").
    """
    
    try:
        response = model.generate_content(instruction)
        visual_idea = response.text.strip()
        print(f"💡 Gemini Concept: {visual_idea}")
        return visual_idea
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return "A glowing glass hexagon"

def generate_image_hf(visual_description):
    print(f"🎨 Generating Icon with SDXL...")
    
    # Combine template + object
    final_prompt = f"{STYLE_TEMPLATE} {visual_description}, centered composition."
    print(f"📝 Prompt: {final_prompt}")
    
    headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}
    
    payload = {
        "inputs": final_prompt,
        "parameters": {
            "negative_prompt": "text, words, letters, complex, messy, blurry, low quality, deformed, multiple objects, cropped",
            "num_inference_steps": 25,
            "guidance_scale": 7.0
        }
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        
        if response.status_code == 503:
            print("⏳ Model loading, waiting 20s...")
            time.sleep(20)
            response = requests.post(HF_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
            return None
            
        return response.content
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def save_image(image_bytes, output_path="assets/architecture_diagram.png"):
    if not image_bytes:
        return
    print(f"💾 Saving to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.save(output_path)
        print("✅ Image saved!")
    except Exception as e:
        print(f"❌ Save Error: {e}")

if __name__ == "__main__":
    if not os.getenv("HF_TOKEN"):
        print("❌ Error: Missing HF_TOKEN.")
        exit(1)

    code_ctx = get_code_context()
    scene_desc = analyze_and_prompt(code_ctx)
    img_bytes = generate_image_hf(scene_desc)
    save_image(img_bytes)
