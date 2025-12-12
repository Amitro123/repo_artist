from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables FIRST so that auth module can read them
load_dotenv()

from web.backend import auth, api

app = FastAPI(title="Repo-Artist Web API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api")

# Serve React App
# Correct path to dist folder: repo_artist/web/frontend/dist
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Ensure static dir exists
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount /static for generated images
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount assets if they exist (Vite puts js/css in /assets)
if os.path.exists(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

@app.get("/")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"error": f"Frontend build not found at {index_path}. Run 'npm run build' in web/frontend."})

@app.get("/auth/login")
def login_redirect():
    return {"url": auth.get_login_url()}

@app.get("/auth/callback")
async def auth_callback(code: str):
    """
    Exchanges code for token and redirects to frontend with token in params.
    """
    try:
        token = await auth.exchange_code_for_token(code)
        # Redirect to root with token
        return RedirectResponse(url=f"/?access_token={token}")
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("web.backend.main:app", host="0.0.0.0", port=8000, reload=True)
