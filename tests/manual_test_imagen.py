#!/usr/bin/env python3
"""
Imagen 3 Debug Script

Tests Vertex AI connection and Imagen 3 image generation.
Helps diagnose authentication, API, and model issues.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 80)
print("🔍 Imagen 3 Connection Debugger")
print("=" * 80)

# Step 1: Check Environment Variables
print("\n📋 Step 1: Checking Environment Variables")
print("-" * 80)

project_id = os.getenv("IMAGEN_PROJECT_ID")
location = os.getenv("IMAGEN_LOCATION", "us-central1")
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

print(f"IMAGEN_PROJECT_ID: {project_id or '❌ NOT SET'}")
print(f"IMAGEN_LOCATION: {location}")
print(f"GOOGLE_APPLICATION_CREDENTIALS: {credentials_path or '❌ NOT SET'}")

if not project_id:
    print("\n❌ ERROR: IMAGEN_PROJECT_ID is not set in .env file")
    sys.exit(1)

if not credentials_path:
    print("\n❌ ERROR: GOOGLE_APPLICATION_CREDENTIALS is not set in .env file")
    sys.exit(1)

# Check if credentials file exists
creds_file = Path(credentials_path)
if not creds_file.exists():
    print(f"\n❌ ERROR: Credentials file not found: {credentials_path}")
    sys.exit(1)
else:
    print(f"✅ Credentials file exists: {creds_file.absolute()}")

# Step 2: Test Google Cloud Authentication
print("\n🔐 Step 2: Testing Google Cloud Authentication")
print("-" * 80)

try:
    from google.cloud import aiplatform
    print("✅ google-cloud-aiplatform package imported successfully")
except ImportError as e:
    print(f"❌ ERROR: Failed to import google-cloud-aiplatform: {e}")
    print("\nInstall with: pip install google-cloud-aiplatform")
    sys.exit(1)

try:
    # Initialize Vertex AI
    aiplatform.init(project=project_id, location=location)
    print(f"✅ Vertex AI initialized successfully")
    print(f"   Project: {project_id}")
    print(f"   Location: {location}")
except Exception as e:
    print(f"❌ ERROR: Failed to initialize Vertex AI: {e}")
    print("\nPossible issues:")
    print("1. Vertex AI API not enabled in Google Cloud Console")
    print("2. Service account lacks permissions")
    print("3. Billing not enabled on the project")
    sys.exit(1)

# Step 3: Check Available Models
print("\n📦 Step 3: Checking Imagen Model Availability")
print("-" * 80)

try:
    from vertexai.preview.vision_models import ImageGenerationModel
    print("✅ ImageGenerationModel imported successfully")
    
    # Try different model names
    model_names = [
        "imagen-3.0-generate-001",
        "imagegeneration@006",
        "imagen-3.0-fast-generate-001",
    ]
    
    print("\nTrying different model names:")
    working_model = None
    
    for model_name in model_names:
        try:
            print(f"\n  Testing: {model_name}")
            model = ImageGenerationModel.from_pretrained(model_name)
            print(f"  ✅ Model loaded successfully: {model_name}")
            working_model = model_name
            break
        except Exception as e:
            print(f"  ❌ Failed: {e}")
    
    if not working_model:
        print("\n❌ ERROR: None of the model names worked")
        print("\nPlease check:")
        print("1. Vertex AI API is enabled")
        print("2. Your region supports Imagen 3")
        print("3. Your service account has 'Vertex AI User' role")
        sys.exit(1)
    
    print(f"\n✅ Using model: {working_model}")
    
except Exception as e:
    print(f"❌ ERROR: Failed to load ImageGenerationModel: {e}")
    sys.exit(1)

# Step 4: Test Image Generation
print("\n🎨 Step 4: Testing Image Generation")
print("-" * 80)

try:
    print("\nGenerating test image: 'A simple red cube on white background'")
    print("This may take 30-60 seconds...")
    
    model = ImageGenerationModel.from_pretrained(working_model)
    
    response = model.generate_images(
        prompt="A simple red cube on white background, 3D render, clean, minimalist",
        number_of_images=1,
        aspect_ratio="1:1",
    )
    
    print("✅ Image generation request completed")
    
    # Check response
    if hasattr(response, 'images') and response.images:
        print(f"✅ Received {len(response.images)} image(s)")
        
        # Save test image
        test_output = "test_imagen_output.png"
        image_bytes = response.images[0]._image_bytes
        
        with open(test_output, 'wb') as f:
            f.write(image_bytes)
        
        print(f"✅ Test image saved to: {test_output}")
        print(f"   Size: {len(image_bytes)} bytes")
        
    else:
        print("❌ ERROR: Response has no images")
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {dir(response)}")
        
except Exception as e:
    print(f"❌ ERROR: Image generation failed: {e}")
    print(f"\nError type: {type(e).__name__}")
    
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
    
    print("\n💡 Common issues:")
    print("1. Quota exceeded - check Google Cloud Console quotas")
    print("2. Billing not enabled")
    print("3. Service account lacks 'Vertex AI User' role")
    print("4. Region doesn't support Imagen 3")
    print("5. API temporarily unavailable (503 errors)")
    sys.exit(1)

# Success!
print("\n" + "=" * 80)
print("✅ SUCCESS! Imagen 3 is working correctly!")
print("=" * 80)
print(f"\nWorking configuration:")
print(f"  Model: {working_model}")
print(f"  Project: {project_id}")
print(f"  Location: {location}")
print(f"\nYou can now use Imagen 3 in the main application!")
print("=" * 80)
