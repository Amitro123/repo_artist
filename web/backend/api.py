from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from typing import Optional
import git
import sys
import os
import shutil
import tempfile
import base64
import uuid
from pathlib import Path

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_PREVIEWS_DIR = os.path.join(BASE_DIR, "web", "static", "previews")

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from repo_artist.core import (
    get_code_context,
    analyze_architecture,
    build_hero_prompt,
    generate_hero_image_pollinations,
    generate_hero_image_mermaid,
    update_readme_content,
    DEFAULT_MODEL
)
from web.backend.github_utils import create_or_update_file, get_default_branch

router = APIRouter()

class PreviewRequest(BaseModel):
    repo_url: str
    gemini_api_key: Optional[str] = None # Optional now
    branch: Optional[str] = None
    force_reanalyze: bool = False  # NEW: Ignore cached architecture JSON

class ApplyRequest(BaseModel):
    repo_url: str
    approved_readme: str
    image_data_b64: str
    branch: Optional[str] = None
    commit_message: str = "🤖 [Repo-Artist] Add architecture hero image"

class RefineRequest(BaseModel):
    repo_url: str
    edit_prompt: str  # e.g., "Make the database red"
    gemini_api_key: Optional[str] = None
    original_prompt: Optional[str] = None  # If available from cache
    force_reanalyze: bool = False  # NEW: Ignore cached architecture JSON

@router.get("/config")
def get_config():
    """Returns frontend configuration flags"""
    print("[API] /config endpoint called", flush=True)
    has_key = bool(os.getenv("GEMINI_API_KEY"))
    return {"has_env_key": has_key}

@router.post("/preview")
async def preview_architecture(req: PreviewRequest):
    """
    1. Clone repo to temp local dir
    2. Analyze architecture
    3. Generate image
    4. Generate README preview
    """
    print(f"[API] /preview endpoint called - repo: {req.repo_url}", flush=True)
    
    # Fallback to server-side key
    api_key = req.gemini_api_key or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required (not found in request or env)")

    temp_dir = tempfile.mkdtemp()
    try:
        # Clone Repo
        print(f"Cloning {req.repo_url} to {temp_dir}...")
        try:
            repo = git.Repo.clone_from(req.repo_url, temp_dir, depth=1, branch=req.branch or 'main') # Try main first
        except Exception:
            try:
                # Fallback to master if main fails and branch wasn't specified
                if not req.branch:
                    repo = git.Repo.clone_from(req.repo_url, temp_dir, depth=1, branch='master')
                else:
                    raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to clone repository: {str(e)}")

        # Core Logic
        structure = get_code_context(temp_dir)
        architecture = analyze_architecture(
            structure, 
            api_key=api_key,
            force_refresh=True,
            force_reanalyze=req.force_reanalyze,  # NEW
            repo_path=temp_dir  # NEW: Enable persistent JSON caching
        )
        
        if not architecture:
             raise HTTPException(status_code=500, detail="Failed to analyze architecture")
             
        prompt = build_hero_prompt(architecture)
        
        # Generate Image (Pollinations)
        image_content = generate_hero_image_pollinations(prompt)
        image_b64 = None
        if image_content:
             image_b64 = base64.b64encode(image_content).decode('utf-8')
        else:
            # Fallback
             mermaid_content = generate_hero_image_mermaid(architecture)
             if mermaid_content:
                 image_b64 = base64.b64encode(mermaid_content).decode('utf-8')
        
        if not image_b64:
             raise HTTPException(status_code=500, detail="Failed to generate image")

        # Save to static file for persistent preview (Fixes 404)
        try:
            os.makedirs(STATIC_PREVIEWS_DIR, exist_ok=True)
            image_id = str(uuid.uuid4())
            filename = f"{image_id}.png"
            file_path = os.path.join(STATIC_PREVIEWS_DIR, filename)
            
            # Decode b64 to save bytes (since we encode it above)
            # Actually we likely have content in image_content or mermaid_content variables but logic above is branchy
            # Let's just decode the b64 we just made to be sure
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(image_b64))
                
            image_url = f"/static/previews/{filename}"
            print(f"✅ Saved preview to {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to save static preview: {e}")
            image_url = None

        # Read current README
        readme_content = ""
        readme_path = os.path.join(temp_dir, "README.md")
        if os.path.exists(readme_path):
             with open(readme_path, 'r', encoding='utf-8') as f:
                 readme_content = f.read()
        
        # Generate new README content
        new_readme = update_readme_content(readme_content)
        
        return {
            "image_b64": image_b64,
            "image_url": image_url,
            "current_readme": readme_content,
            "new_readme": new_readme,
            "architecture": architecture
        }
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True) # Cleanup

@router.post("/apply")
async def apply_changes(req: ApplyRequest, authorization: Optional[str] = Header(None)):
    """
    Commit changes to GitHub.
    Uses github_utils to update README.md and upload asset image.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    # Parse owner/repo
    # e.g. https://github.com/owner/repo or owner/repo
    parts = req.repo_url.strip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid repo URL")
    
    repo_name = parts[-1]
    owner = parts[-2]
    
    target_branch = req.branch
    if not target_branch:
         target_branch = await get_default_branch(owner, repo_name, token)

    # 1. Upload Image
    image_bytes = base64.b64decode(req.image_data_b64)
    image_path = "assets/architecture_diagram.png"
    
    print(f"Uploading image to {owner}/{repo_name}/{image_path} on branch {target_branch}")
    await create_or_update_file(
        owner, repo_name, image_path, image_bytes, 
        message="[Repo-Artist] Add hero image asset", 
        token=token, 
        branch=target_branch
    )
    
    # 2. Update README
    # Convert string content to bytes
    readme_bytes = req.approved_readme.encode('utf-8')
    
    print(f"Updating README.md on {owner}/{repo_name}")
    resp = await create_or_update_file(
        owner, repo_name, "README.md", readme_bytes,
        message=req.commit_message,
        token=token,
        branch=target_branch
    )
    
    commit_url = resp.get("commit", {}).get("html_url")
    return {"status": "success", "commit_url": commit_url}

@router.post("/refine-image")
async def refine_image(req: RefineRequest):
    """
    Refine an existing generated image using natural language.
    Regenerates the image with an enhanced prompt.
    """
    print(f"[API] /refine-image endpoint called - edit: {req.edit_prompt}", flush=True)
    
    # Fallback to server-side key
    api_key = req.gemini_api_key or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Clone repo to get architecture context
        print(f"Cloning {req.repo_url} for refinement...")
        try:
            repo = git.Repo.clone_from(req.repo_url, temp_dir, depth=1, branch='main')
        except Exception:
            try:
                repo = git.Repo.clone_from(req.repo_url, temp_dir, depth=1, branch='master')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to clone repository: {str(e)}")
        
        # Get code context and architecture
        print("Analyzing architecture...")
        context = get_code_context(temp_dir)
        architecture = analyze_architecture(
            context, 
            api_key, 
            model=DEFAULT_MODEL,
            force_reanalyze=req.force_reanalyze,  # NEW
            repo_path=temp_dir  # NEW: Enable persistent JSON caching
        )
        
        # Build original hero prompt
        original_prompt = build_hero_prompt(architecture)
        
        # Enhance prompt with user's refinement
        enhanced_prompt = f"{original_prompt}\n\nAdditional style requirements: {req.edit_prompt}"
        
        print(f"Generating refined image with prompt enhancement...")
        print(f"Original prompt length: {len(original_prompt)} chars")
        print(f"Enhanced prompt length: {len(enhanced_prompt)} chars")
        
        # Generate new image with enhanced prompt
        image_bytes = generate_hero_image_pollinations(enhanced_prompt)
        
        if not image_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate refined image")
        
        # Save refined image
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Save to static directory
        os.makedirs(STATIC_PREVIEWS_DIR, exist_ok=True)
        filename = f"{uuid.uuid4()}.png"
        file_path = os.path.join(STATIC_PREVIEWS_DIR, filename)
        
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        image_url = f"/static/previews/{filename}"
        print(f"✅ Saved refined image to {file_path}")
        
        return {
            "image_b64": image_b64,
            "image_url": image_url,
            "enhanced_prompt": enhanced_prompt
        }
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
