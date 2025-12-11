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
STYLE_TEMPLATE = """
A hyper-realistic, premium 3D technical architecture visualization in an isometric view. 
The aesthetic is dark mode sci-fi, glowing with neon energy. 
The color palette features a distinct transition from electric cyan and neon blue (for inputs) to deep neon purple and magenta (for processing).
The environment is a reflective, futuristic circuit board platform floating in a dark data nebula. 
Key elements are complex, glowing 3D structures encased in glass and energy fields, casting volumetric light. 
Connections are thick, translucent, volumetric data conduits (pipes) with visible pulses of light. 
High-end CGI, intense bloom, subsurface scattering, realistic reflections, octane render, 8k.
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
    """Uses Gemini to create the specific scene description."""
    print("🧠 Analyzing architecture with Gemini...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ GEMINI_API_KEY missing, using generic prompt.")
        return "A central glowing cubic hub receives blue data pipes and sends purple data pipes to a glowing brain-shaped AI model."

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    instruction = f"""
    You are an Art Director for a Sci-Fi Tech Visualization. 
    Your goal: Create a prompt for Stable Diffusion XL that visualizes this SPECIFIC codebase as a 3D architecture.
    
    CRITICAL: Do NOT write a long narrative. Write a PUNCHY, VISUAL list of elements.
    
    Identify 3-4 MAJOR components from the code:
    1. The Trigger/Input (e.g., User, GitHub Action, CLI)
    2. The Logic Core (e.g., Python Script, Controller)
    3. The AI Brain (e.g., Gemini, LLM)
    4. The Output (e.g., Image, File, Database)
    
    OUTPUT FORMAT:
    "Isometric 3D render. In the center, a [VSUAL_1] labeled '[NAME_1]'. Connected by [COLOR] data pipes to a [VISUAL_2] on the left labeled '[NAME_2]'. On the right, a [VISUAL_3] labeled '[NAME_3]' glows with [COLOR] energy. Background is a dark data void."
    
    VISUAL GLOSSARY (Use these):
    - Python Script = "Crystalline Cube"
    - API/AI = "Glowing Neural Orb"
    - Database/File = "Holographic Glass Block"
    - User/Trigger = "Neon Control Interface"
    
    NOW ANALYZE THIS CODEBASE:
    {code_context}
    
    OUTPUT ONLY THE PROMPT. Keep it under 75 words.
    """
    
    try:
        response = model.generate_content(instruction)
        return response.text.strip()
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
