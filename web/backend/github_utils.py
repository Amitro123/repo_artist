import httpx
import base64
from typing import Optional, List, Dict, Any
from fastapi import HTTPException

API_BASE = "https://api.github.com"


async def get_repo_tree(owner: str, repo: str, token: Optional[str] = None, branch: str = "main") -> List[Dict[str, Any]]:
    """
    Fetch repository file tree using GitHub API (no clone required).
    
    This is much more efficient than cloning the entire repository,
    especially for large repos or high traffic scenarios.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: Optional GitHub token (for private repos or higher rate limits)
        branch: Branch to fetch tree from
        
    Returns:
        List of file/directory entries with path, type, and size
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with httpx.AsyncClient() as client:
        # First get the branch ref to find the tree SHA
        resp = await client.get(
            f"{API_BASE}/repos/{owner}/{repo}/git/ref/heads/{branch}",
            headers=headers
        )
        
        if resp.status_code != 200:
            # Try master if main fails
            if branch == "main":
                resp = await client.get(
                    f"{API_BASE}/repos/{owner}/{repo}/git/ref/heads/master",
                    headers=headers
                )
                if resp.status_code != 200:
                    raise HTTPException(status_code=400, detail=f"Failed to fetch branch ref: {resp.text}")
            else:
                raise HTTPException(status_code=400, detail=f"Failed to fetch branch ref: {resp.text}")
        
        commit_sha = resp.json()["object"]["sha"]
        
        # Get the tree recursively
        resp = await client.get(
            f"{API_BASE}/repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1",
            headers=headers
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch tree: {resp.text}")
        
        tree_data = resp.json()
        return tree_data.get("tree", [])


async def get_file_content(owner: str, repo: str, path: str, token: Optional[str] = None, branch: str = "main") -> Optional[str]:
    """
    Fetch a single file's content from GitHub API.
    
    Args:
        owner: Repository owner
        repo: Repository name
        path: File path within the repo
        token: Optional GitHub token
        branch: Branch to fetch from
        
    Returns:
        File content as string, or None if not found
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/repos/{owner}/{repo}/contents/{path}?ref={branch}",
            headers=headers
        )
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        if data.get("encoding") == "base64" and data.get("content"):
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        
        return None


def tree_to_code_context(tree: List[Dict[str, Any]], max_depth: int = 3) -> str:
    """
    Convert GitHub API tree response to code context string format.
    
    Args:
        tree: List of tree entries from GitHub API
        max_depth: Maximum directory depth to include
        
    Returns:
        Formatted string representation of the file structure
    """
    # Filter and organize entries
    ignore_dirs = {'.git', 'node_modules', 'venv', '.venv', '__pycache__', 
                   'assets', '.github', '.idea', 'tests', 'dist', 'build',
                   'coverage', '.pytest_cache', '.mypy_cache', '.tox', 'eggs'}
    
    important_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.rb',
                           '.json', '.md', '.yml', '.yaml', '.toml', '.sql', '.sh'}
    
    important_files = {'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
                       'Makefile', 'requirements.txt', 'package.json', 'Cargo.toml',
                       'go.mod', 'pom.xml', 'build.gradle'}
    
    structure = []
    seen_dirs = set()
    
    for entry in tree:
        path = entry.get("path", "")
        entry_type = entry.get("type", "")
        
        # Skip ignored directories
        parts = path.split("/")
        if any(part in ignore_dirs for part in parts):
            continue
        
        # Check depth
        depth = len(parts) - 1
        if depth > max_depth:
            continue
        
        indent = "  " * depth
        
        if entry_type == "tree":  # Directory
            dir_path = path
            if dir_path not in seen_dirs:
                seen_dirs.add(dir_path)
                folder_name = parts[-1]
                structure.append(f"{indent}📁 {folder_name}/")
        
        elif entry_type == "blob":  # File
            filename = parts[-1]
            ext = "." + filename.split(".")[-1] if "." in filename else ""
            
            # Check if file is important
            if ext.lower() in important_extensions or filename in important_files:
                # Ensure parent directories are shown
                for i in range(len(parts) - 1):
                    parent_path = "/".join(parts[:i+1])
                    if parent_path not in seen_dirs:
                        seen_dirs.add(parent_path)
                        parent_indent = "  " * i
                        structure.append(f"{parent_indent}📁 {parts[i]}/")
                
                structure.append(f"{indent}  📄 {filename}")
    
    return "\n".join(structure)


async def get_default_branch(owner: str, repo: str, token: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/repos/{owner}/{repo}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch repo info")
        return resp.json().get("default_branch", "main")

async def get_file_sha(owner: str, repo: str, path: str, token: str, branch: str = "main"):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/repos/{owner}/{repo}/contents/{path}?ref={branch}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
        )
        if resp.status_code == 200:
            return resp.json().get("sha")
        return None

async def create_or_update_file(
    owner: str, repo: str, path: str, content: bytes, message: str, token: str, branch: str = "main"
):
    sha = await get_file_sha(owner, repo, path, token, branch)
    
    # Check if content is text or binary? content is bytes.
    # GitHub API expects base64 encoded content
    content_b64 = base64.b64encode(content).decode("utf-8")
    
    data = {
        "message": message,
        "content": content_b64,
        "branch": branch
    }
    if sha:
        data["sha"] = sha
        
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.put(
            f"{API_BASE}/repos/{owner}/{repo}/contents/{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
            json=data
        )
        
        if resp.status_code not in (200, 201):
             raise HTTPException(status_code=400, detail=f"Failed to write file {path}: {resp.text}")
             
        return resp.json()
