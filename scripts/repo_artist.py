import os
import requests
import io
from PIL import Image
import google.generativeai as genai
from pathlib import Path
import time

# --- CONFIGURATION ---
HF_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
# UPDATED URL HERE:
HF_API_URL = f"https://router.huggingface.co/models/{HF_MODEL_ID}"

# סגנון נקי, זכוכית, ללא טקסט, רק ויזואליה חזקה
STYLE_TEMPLATE = """
A single high-quality 3D glassmorphism object floating in the center. 
Dark background, soft studio lighting, neon rim light, octane render. 
Frosted glass texture, semi-transparent, glowing edges. 
Minimalist, modern UI design, 8k render. 
NO text, NO letters. 
Subject:
"""

def get_code_context(root_dir="."):
    """Mock context extraction."""
    file_list = []
    for root, dirs, files in os.walk(root_dir):
        if '.git' in root: continue
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.md', '.yml')):
                file_list.append(file)
    return ", ".join(file_list[:50])

def analyze_and_prompt(code_context):
    print("🧠 Choosing the Hero Object with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        return "A glowing glass cube."

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    instruction = f"""
    Analyze these filenames to understand the project type.
    Choose ONE single physical object to represent it as a 3D Glass Icon.
    
    - If Automation/Bot -> "A futuristic glass gear system"
    - If AI/Brain -> "A glowing crystal brain structure"
    - If Web/Code -> "A glass isometric code bracket symbol"
    - If Security -> "A glass shield with a neon lock"
    - If CLI -> "A floating glass command terminal prompt"
    
    Filenames: {code_context}
    
    Output ONLY the object description.
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
    
    final_prompt = f"{STYLE_TEMPLATE} {visual_description}, centered composition."
    print(f"📝 Prompt: {final_prompt}")
    
    headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}
    
    payload = {
        "inputs": final_prompt,
        "parameters": {
            "negative_prompt": "text, words, letters, signature, watermark, complex, messy, blurry, low quality, deformed, multiple objects, cropped",
            "num_inference_steps": 28,
            "guidance_scale": 7.5
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

def save_image(image_bytes, output_path="assets/banner.png"):
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
