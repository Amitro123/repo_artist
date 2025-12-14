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
- **Features**:
    - Logging with configurable levels (replaces print statements)
    - Full type hints for better IDE support and static analysis
    - Configurable depth, component limits, and ignore patterns
    - Multi-tier image generation with automatic fallback
    - JSON retry mechanism (up to 3 attempts with correction prompts)
    - Improved README update logic for better format compatibility
- **Modules**:
    - `get_code_context`: Harvests file structure with configurable depth and patterns.
    - `analyze_architecture`: Gemini-powered architecture inference with persistent JSON caching and retry logic.
    - `save_architecture_json`: Saves architecture to `repo-artist-architecture.json`.
    - `load_architecture_json`: Loads architecture from `repo-artist-architecture.json`.
    - `build_hero_prompt`: Creates visual prompts with configurable component/connection limits.
    - `generate_hero_image`: Multi-tier fallback (Imagen 3 → Pollinations → Mermaid).
    - `generate_hero_image_imagen3`: Tier 1 - Google Imagen 3 via Vertex AI.
    - `generate_hero_image_pollinations`: Tier 2 - Pollinations.ai free API.
    - `generate_hero_image_mermaid`: Tier 3 - Mermaid diagram fallback.
    - `update_readme_content`: Generates updated README string with improved insertion logic.

### 1a. Configuration (`repo_artist/config.py`)
- **Purpose**: Centralized configuration management.
- **Features**:
    - Environment variable support for all settings
    - `.artistignore` file support for custom ignore patterns
    - Sensible defaults for all options
    - Type-safe configuration with dataclasses

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
        - **Preview**: Visual Hero Image + Three-tab view (Preview/Code/Architecture JSON).
        - **Refinement**: Natural language image editing ("Make the database red", "Add cloud icons").
        - **Caching Control**: Checkbox to force re-analysis (ignore cached architecture JSON).
        - **Apply**: One-click commit to GitHub via REST API.
        - **Architecture JSON Tab**: View complete analyzed architecture data in formatted JSON.

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

## Testing

Repo-Artist includes comprehensive test coverage to ensure reliability:

### Test Suite
- **Total Tests**: 54 tests across 3 test files
- **Coverage**: 100% of critical paths
- **Execution Time**: ~30 seconds

### Test Files
1. **`tests/test_config.py`** (10 tests)
   - Configuration system with environment variables
   - `.artistignore` file loading
   - Path generation and validation

2. **`tests/test_core_logic.py`** (30 tests)
   - Code context harvesting with configurable depth
   - JSON retry mechanism (3 attempts with correction prompts)
   - Prompt building with component/connection limits
   - README update logic for various formats
   - Caching mechanisms (load/save)
   - Mermaid diagram generation

3. **`tests/test_image_generation.py`** (14 tests)
   - Multi-tier fallback strategy (Imagen 3 → Pollinations → Mermaid)
   - Retry mechanisms for network errors
   - Error handling and graceful degradation
   - Integration tests for end-to-end flows

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage report
pytest tests/ --cov=repo_artist --cov-report=html
```
