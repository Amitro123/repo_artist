# Repo-Artist Specification

## Overview
Repo-Artist is an automation tool that automatically generates a "Hero Image" for a GitHub repository based on the code structure. It uses a robust multi-tier fallback pipeline to ensuring high-quality visualization suitable for READMEs even without premium API keys.

## Tech Stack
- **Analysis**: Google Gemini (Default: `gemini-2.5-flash`, Configurable)
- **Image Gen**: 
    - **Tier 1 (Premium)**: Google Imagen 3 (Vertex AI / Gemini API)
    - **Tier 2 (Free)**: Pollinations.ai (Flux Model - HTTP API)
    - **Tier 3 (Fallback)**: Mermaid.js diagram
- **CI/CD**: GitHub Actions
- **Language**: Python 3.10+

## Components

### 1. Local Trigger (`smart_push.py`)
- Wraps `git push`.
- Detects architecture changes (> 50 lines or > 3 files).
- Prompts user (`y/N`) to generate art.
- Options:
    1.  **Full Refresh**: Re-analyze architecture & regenerate image.
    2.  **Reuse Architecture**: Only regenerate image (faster).
- Adds `[GEN_ART]` tag to commit.

### 2. Core Logic (`scripts/repo_artist.py`)
- **Inputs**: `GEMINI_API_KEY`, `ARCH_MODEL_NAME` (Optional).
- **Process**:
    1.  **Harvest**: Walk directory for code files (smart filtering).
    2.  **Analyze**: Send semantic structure to Gemini → JSON Graph.
        - *Caching*: Stores result in `assets/architecture.json`.
    3.  **Synthesize**: Build "Sci-Fi Isometric Flow" prompt dynamically.
    4.  **Generate**: Multi-tier execution (Imagen → Pollinations → Mermaid).
    5.  **Update**: Inserts/updates hero image in `README.md`.
- **Style**: High-end sci-fi isometric flow diagram, dark UI, neon blue/magenta, glass platforms.

### 3. CI Pipeline (`.github/workflows/generate_art.yml`)
- Trigger: Push with `[GEN_ART]` or Manual Dispatch.
- Action: Install deps -> Run script -> Commit image & JSON.
- Secrets: `GEMINI_API_KEY`, `ARCH_MODEL_NAME`.

## Setup
1.  Install dependencies: `pip install -r requirements.txt`
2.  Set environment variables:
    - Copy `.env.example` to `.env`.
    - Set `GEMINI_API_KEY` (Get from [Google AI Studio](https://aistudio.google.com/app/apikey)).
    - (Optional) Set `ARCH_MODEL_NAME` to override module (e.g., `gemini-2.0-flash`).
3.  Use `python smart_push.py` instead of `git push`.
