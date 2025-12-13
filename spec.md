# Repo-Artist Specification

## Overview
Repo-Artist is an automation tool that automatically generates a "Hero Image" for a GitHub repository based on the code structure. It uses a robust multi-tier fallback pipeline to ensuring high-quality visualization suitable for READMEs even without premium API keys.

## Tech Stack
- **Analysis**: Google Gemini (Default: `gemini-2.5-flash`, Configurable)
- **Image Gen**: 
    - **Tier 1 (Premium)**: Google Imagen 3 (Vertex AI / Gemini API)
    - **Tier 2 (Free)**: Pollinations.ai (Flux Model - HTTP API)
    - **Tier 3 (Fallback)**: Mermaid.js diagram
- **Backend**: FastAPI, Uvicorn, GitHub OAuth
- **Frontend**: React, Vite, TypeScript, Tailwind CSS (Single Page App)
- **CI/CD**: GitHub Actions
- **Language**: Python 3.10+

## Components

### 1. Core Logic (`repo_artist/core.py`)
- **Purpose**: Pure business logic library, reusable by CLI and Web App.
- **Modules**:
    - `get_code_context`: Harvests file structure.
    - `analyze_architecture`: Gemini-powered architecture inference with persistent JSON caching.
    - `save_architecture_json`: Saves architecture to `repo-artist-architecture.json`.
    - `load_architecture_json`: Loads architecture from `repo-artist-architecture.json`.
    - `build_hero_prompt`: Creates visual prompts.
    - `generate_hero_image_*`: Handles image generation providers.
    - `update_readme_content`: Generates updated README string.

### 2. CLI Tools
- **Setup Wizard (`scripts/repo_artist_setup.py`)**:
    - Interactive configuration for `.env`.
    - Guides GitHub OAuth App creation.
    - Auto-launches Web App.
- **Logic CLI (`scripts/cli.py`)**:
    - `generate`: Analyze repo -> generate image -> update README.
    - `setup-ci`: Configure GitHub Actions workflow.

### 3. Web Application (`web/`)
- **Backend (`web/backend/`)**:
    - **FastAPI**: Serves API and React Static Files.
    - **Router**: `/api` for logic, `/auth` for GitHub OAuth, `/` serves SPA.
    - **Auth**: GitHub OAuth flow (Login -> Callback -> Token).
- **Frontend (`web/frontend/`)**:
    - **Stack**: React + Vite + TypeScript.
    - **UI**: Modern Dark Mode, Cyberpunk/Glassmorphism aesthetics.
    - **Features**:
        - **Configuration**: Interactive inputs for Repo URL & Gemini Key.
        - **Preview**: Visual Hero Image + Markdown Render + Diff View.
        - **Refinement**: Natural language image editing ("Make the database red", "Add cloud icons").
        - **Caching Control**: Checkbox to force re-analysis (ignore cached architecture JSON).
        - **Apply**: One-click commit to GitHub via REST API.

### 4. Local Trigger (`smart_push.py`)
- Wraps `git push`.
- Detects architecture changes (> 50 lines or > 3 files).
- Options: Full Refresh vs Rewrite Only.
- Adds `[GEN_ART]` tag to commit.

### 5. CI Pipeline (`.github/workflows/generate_art.yml`)
- Trigger: Push with `[GEN_ART]` or Manual Dispatch.
- Action: Install deps -> Run CLI script -> Commit image & JSON.
- Secrets: `GEMINI_API_KEY`, `ARCH_MODEL_NAME`.

## Setup
1.  **Install dependencies**: `pip install -r requirements.txt` (and `npm install` in frontend).
2.  **Run Setup Wizard**:
    ```bash
    python scripts/repo_artist_setup.py
    ```
    (Handles `.env`, GitHub OAuth, and Server Launch).

3.  **Manual Launch**:
    - Backend: `uvicorn web.backend.main:app --reload`
    - Frontend Dev: `cd web/frontend && npm run dev`
