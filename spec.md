# Repo-Artist Specification

## Overview
Repo-Artist is an automation tool that automatically generates a "Hero Image" for a GitHub repository based on the code structure.

## Tech Stack
- **Analysis**: Google Gemini 1.5 Flash
- **Image Gen**: Flux.1 Schnell (Replicate)
- **CI/CD**: GitHub Actions
- **Language**: Python 3.10+

## Components

### 1. Local Trigger (`smart_push.py`)
- Wraps `git push`.
- Detects architecture changes (> 50 lines or > 3 files).
- Prompts user (`y/N`) to generate art.
- Adds `[GEN_ART]` tag to commit if yes.

### 2. Core Logic (`scripts/repo_artist.py`)
- **Inputs**: `GEMINI_API_KEY`, `REPLICATE_API_TOKEN`.
- **Process**:
    1.  **Harvest**: Walk directory for code files.
    2.  **Analyze**: Send code to Gemini with `STYLE_TEMPLATE`.
    3.  **Generate**: Send prompt to Replicate.
    4.  **Save**: `assets/architecture_diagram.png`.
- **Style**: Dark mode sci-fi, isometric, neon energy.

### 3. CI Pipeline (`.github/workflows/generate_art.yml`)
- Trigger: Push with `[GEN_ART]`.
- Action: Install deps -> Run script -> Commit image.

## Setup
1.  Install dependencies: `pip install -r requirements.txt`
2.  Set environment variables:
    - Copy `.env.example` to `.env`.
    - Set `GEMINI_API_KEY` (Get from [Google AI Studio](https://aistudio.google.com/app/apikey)).
    - Set `REPLICATE_API_TOKEN` (Get from [Replicate](https://replicate.com/account/api-tokens)).
3.  Use `python smart_push.py` instead of `git push`.
