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

# Add request logging middleware
import time
import sys
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware

# Create log file
LOG_FILE = os.path.join(os.path.dirname(__file__), "requests.log")

def log_to_file(message):
    """Write to both stdout and file"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    full_message = f"{timestamp} - {message}"
    print(full_message, flush=True, file=sys.stdout)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(full_message + "\n")
    except:
        pass

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log incoming request
        log_to_file(f"→ {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            log_to_file(f"← {request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
            
            return response
        except Exception as e:
            log_to_file(f"✗ {request.method} {request.url.path} - ERROR: {str(e)}")
            raise

# Add the logging middleware
app.add_middleware(LoggingMiddleware)

# Startup event to confirm middleware is loaded
@app.on_event("startup")
async def startup_event():
    log_to_file("="*80)
    log_to_file("🎯 REQUEST LOGGING ENABLED - Logs will appear below AND in requests.log")
    log_to_file("="*80)

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

@app.get("/favicon.ico")
async def favicon():
    """Return 204 No Content for favicon to avoid 404 logs"""
    from fastapi.responses import Response
    return Response(status_code=204)

@app.get("/vite.svg")
async def vite_svg():
    """Return 204 No Content for vite.svg to avoid 404 logs"""
    from fastapi.responses import Response
    return Response(status_code=204)

if __name__ == "__main__":
    uvicorn.run("web.backend.main:app", host="0.0.0.0", port=8000, reload=True)
