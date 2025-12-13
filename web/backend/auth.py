import os
import httpx
from fastapi import HTTPException
from pydantic import BaseModel

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# If running locally vs prod, redirect URI might change
REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/auth/callback")

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    scope: str

def get_login_url():
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
    
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "repo workflow write:packages read:user user:email",
        "state": "random_string_here" # In prod reduce CSRF with random state
    }
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"https://github.com/login/oauth/authorize?{query}"

async def exchange_code_for_token(code: str):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub secrets not configured")

    async with httpx.AsyncClient() as client:
        # GitHub expects POST to get the token
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to exchange code: {response.text}")
            
        data = response.json()
        if "error" in data:
            raise HTTPException(status_code=400, detail=f"OAuth error: {data.get('error_description')}")
            
        return data.get("access_token")
