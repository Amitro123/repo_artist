from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
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
    generate_hero_image,
    generate_hero_image_pollinations,
    generate_hero_image_mermaid,
    update_readme_content,
    DEFAULT_MODEL
)
from web.backend.github_utils import (
    create_or_update_file, 
    get_default_branch,
    get_repo_tree,
    get_file_content,
    tree_to_code_context
)

router = APIRouter()

# Visual style options for the dropdown
VISUAL_STYLES = {
    "auto": None,  # Let AI decide
    "minimalist": "Clean minimalist design with simple shapes, white space, and subtle colors",
    "cyberpunk": "Cyberpunk neon aesthetic with glowing edges, dark background, and vibrant purple/cyan colors",
    "corporate": "Corporate professional style with clean lines, blues and grays, suitable for business presentations",
    "sketch": "Hand-drawn sketch style with rough lines, organic shapes, and a notebook-paper feel",
    "glassmorphism": "3D glassmorphism with frosted glass effects, floating elements, and soft gradients"
}

class PreviewRequest(BaseModel):
    repo_url: str
    gemini_api_key: Optional[str] = None
    branch: Optional[str] = None
    force_reanalyze: bool = False
    style: str = "auto"  # Visual style: auto, minimalist, cyberpunk, corporate, sketch, glassmorphism

class ApplyRequest(BaseModel):
    repo_url: str
    approved_readme: str
    image_data_b64: str
    branch: Optional[str] = None
    commit_message: str = "🤖 [Repo-Artist] Add architecture hero image"
    architecture_json: Optional[Dict[str, Any]] = None

class RefineRequest(BaseModel):
    repo_url: str
    edit_prompt: str  # e.g., "Make the database red"
    gemini_api_key: Optional[str] = None
    original_prompt: Optional[str] = None
    force_reanalyze: bool = False
    style: str = "auto"  # Visual style: auto, minimalist, cyberpunk, corporate, sketch, glassmorphism


@router.get("/config")
def get_config():
    """Returns frontend configuration flags"""
    print("[API] /config endpoint called", flush=True)
    has_key = bool(os.getenv("GEMINI_API_KEY"))
    return {"has_env_key": has_key}

@router.post("/preview")
async def preview_architecture(req: PreviewRequest):
    """
    1. Fetch repo tree via GitHub API (no clone required - much faster!)
    2. Analyze architecture
    3. Generate image
    4. Generate README preview
    """
    print(f"[API] /preview endpoint called - repo: {req.repo_url}", flush=True)
    
    # Fallback to server-side key
    api_key = req.gemini_api_key or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required (not found in request or env)")

    # Parse owner/repo from URL
    parts = req.repo_url.strip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid repo URL")
    
    repo_name = parts[-1].replace(".git", "")
    owner = parts[-2]
    branch = req.branch or "main"
    
    print(f"Fetching tree for {owner}/{repo_name} via GitHub API (no clone)...")
    
    try:
        # Fetch repo tree via GitHub API - MUCH faster than cloning!
        tree = await get_repo_tree(owner, repo_name, token=None, branch=branch)
        structure = tree_to_code_context(tree)
        
        if not structure:
            raise HTTPException(status_code=400, detail="Failed to fetch repository structure")
        
        print(f"✅ Fetched {len(tree)} entries from GitHub API")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch repository: {str(e)}")

    # Core Logic - analyze architecture
    architecture = analyze_architecture(
        structure, 
        api_key=api_key,
        force_refresh=True,
        force_reanalyze=req.force_reanalyze
    )
    
    if not architecture:
         raise HTTPException(status_code=500, detail="Failed to analyze architecture")
    
    # Get style description for prompt
    style_desc = VISUAL_STYLES.get(req.style.lower(), None) if req.style else None
    
    prompt = build_hero_prompt(architecture, hero_style=style_desc)
    
    # Generate Image
    from repo_artist.config import RepoArtistConfig
    config = RepoArtistConfig.from_env()
    config.force_reanalyze = req.force_reanalyze
    
    # Use temp path for output
    temp_dir = tempfile.mkdtemp()
    try:
        output_path = os.path.join(temp_dir, "architecture_diagram.png")
        
        image_content = generate_hero_image(
            prompt, 
            architecture, 
            output_path=output_path, 
            config=config,
            hero_style=style_desc
        )
        image_b64 = None
        if image_content:
             image_b64 = base64.b64encode(image_content).decode('utf-8')
        
        if not image_b64:
             raise HTTPException(status_code=500, detail="Failed to generate image")

        # Save to static file for persistent preview
        try:
            os.makedirs(STATIC_PREVIEWS_DIR, exist_ok=True)
            image_id = str(uuid.uuid4())
            filename = f"{image_id}.png"
            file_path = os.path.join(STATIC_PREVIEWS_DIR, filename)
            
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(image_b64))
                
            image_url = f"/static/previews/{filename}"
            print(f"✅ Saved preview to {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to save static preview: {e}")
            image_url = None

        # Fetch current README via GitHub API (no clone needed)
        readme_content = await get_file_content(owner, repo_name, "README.md", branch=branch) or ""
        
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
        shutil.rmtree(temp_dir, ignore_errors=True)

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
    
    # 3. Upload Architecture JSON (NEW)
    if req.architecture_json:
        try:
            json_content = json.dumps(req.architecture_json, indent=2).encode('utf-8')
            print(f"Uploading repo-artist-architecture.json to {owner}/{repo_name}")
            await create_or_update_file(
                owner, repo_name, "repo-artist-architecture.json", json_content,
                message="[Repo-Artist] Update architecture JSON cache",
                token=token,
                branch=target_branch
            )
        except Exception as e:
            print(f"⚠️ Failed to upload architecture JSON: {e}")
            # Non-blocking error
    
    commit_url = resp.get("commit", {}).get("html_url")
    return {"status": "success", "commit_url": commit_url}

@router.post("/refine-image")
async def refine_image(req: RefineRequest):
    """
    Refine an existing generated image using natural language.
    Regenerates the image with an enhanced prompt using the SAME
    multi-tier fallback (Imagen3 -> Pollinations -> Mermaid) as /preview.
    
    Uses GitHub API to fetch repo tree - no cloning required!
    """
    print(f"[API] /refine-image endpoint called - edit: {req.edit_prompt}", flush=True)
    
    # Fallback to server-side key
    api_key = req.gemini_api_key or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
    
    # Parse owner/repo from URL
    parts = req.repo_url.strip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid repo URL")
    
    repo_name = parts[-1].replace(".git", "")
    owner = parts[-2]
    
    print(f"Fetching tree for {owner}/{repo_name} via GitHub API for refinement...")
    
    try:
        # Fetch repo tree via GitHub API - MUCH faster than cloning!
        tree = await get_repo_tree(owner, repo_name, token=None, branch="main")
        context = tree_to_code_context(tree)
        
        if not context:
            raise HTTPException(status_code=400, detail="Failed to fetch repository structure")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch repository: {str(e)}")
    
    # Get code context and architecture
    print("Analyzing architecture...")
    architecture = analyze_architecture(
        context, 
        api_key, 
        model_name=DEFAULT_MODEL,
        force_reanalyze=req.force_reanalyze
    )
    
    # Build original hero prompt with style
    style_desc = VISUAL_STYLES.get(req.style.lower(), None) if req.style else None
    original_prompt = build_hero_prompt(architecture, hero_style=style_desc)
    
    # Enhance prompt with user's refinement
    enhanced_prompt = f"{original_prompt}\n\nAdditional style requirements: {req.edit_prompt}"
    
    print(f"Generating refined image with prompt enhancement...")
    print(f"Original prompt length: {len(original_prompt)} chars")
    print(f"Enhanced prompt length: {len(enhanced_prompt)} chars")
    
    # Use the full multi-tier generation (Imagen3 -> Pollinations -> Mermaid)
    from repo_artist.config import RepoArtistConfig
    config = RepoArtistConfig.from_env()
    config.force_reanalyze = True  # Force regeneration, don't use cached image
    
    temp_dir = tempfile.mkdtemp()
    try:
        output_path = os.path.join(temp_dir, "architecture_diagram.png")
        
        image_bytes = generate_hero_image(
            enhanced_prompt, 
            architecture, 
            output_path=output_path, 
            config=config,
            hero_style=style_desc
        )

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

