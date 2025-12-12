import httpx
import base64
from fastapi import HTTPException

API_BASE = "https://api.github.com"

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
        
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{API_BASE}/repos/{owner}/{repo}/contents/{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
            json=data
        )
        
        if resp.status_code not in (200, 201):
             raise HTTPException(status_code=400, detail=f"Failed to write file {path}: {resp.text}")
             
        return resp.json()
