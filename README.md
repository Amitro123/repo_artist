# Repo-Artist

**Automated Architecture Hero Image Generator for GitHub Repositories.**

Repo-Artist analyzes your codebase using **Google Gemini** to understand your architecture, then generates a high-end, sci-fi isometric "Hero Image" for your project.

![Architecture](assets/architecture_diagram.png)

## Features

- **AI-Powered Analysis**: Uses Gemini to analyze your code structure and infer architecture components.
- **Smart Caching**: Architecture analysis is cached to avoid unnecessary LLM calls.
- **Configurable Model**: Choose which Gemini model to use via environment variable.
- **Smart Detection**: Only generates new art when significant changes are detected (> 3 files or > 50 lines).
- **CI Integration**: Runs on `git push` via GitHub Actions when `[GEN_ART]` tag is present.

## Installation

1. Clone the repository.
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3. Set up Environment Variables:
    - Copy `.env.example` to `.env`:
      ```bash
      cp .env.example .env
      ```
    - Fill in your keys in `.env`:
      - `GEMINI_API_KEY`: Get from [Google AI Studio](https://aistudio.google.com/app/apikey).
      - `ARCH_MODEL_NAME` (optional): Model to use (default: `gemini-2.5-flash`).

## Usage

### Local Trigger (Recommended)

Use the wrapper script instead of `git push`:

```bash
python smart_push.py origin main
```

If significant changes are detected, it will offer options:
1. **Full refresh** – New architecture analysis + new image
2. **Reuse cached** – Regenerate image only from cached architecture

### Manual Generation

```bash
# Use cached architecture and image (if exists)
python scripts/repo_artist.py

# Force new architecture analysis
python scripts/repo_artist.py --refresh-architecture

# Force regenerate image from cached architecture
python scripts/repo_artist.py --force-image

# Custom style variation
python scripts/repo_artist.py --force-image --hero-style "more minimal"

# Use mermaid fallback instead of AI image
python scripts/repo_artist.py --mode mermaid
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google AI API key for architecture analysis |
| `ARCH_MODEL_NAME` | No | `gemini-2.5-flash` | Gemini model to use for analysis |
| `REFRESH_ARCHITECTURE` | No | `false` | Force new LLM analysis |
| `FORCE_IMAGE` | No | `false` | Force regenerate image |

### Caching

- **Architecture cache**: `assets/architecture.json` – Stores the analyzed architecture JSON
- **Image cache**: `assets/architecture_diagram.png` – Generated hero image

To bypass caching:
- `--refresh-architecture` – Forces new LLM call, overwrites `architecture.json`
- `--force-image` – Forces new image generation, overwrites `architecture_diagram.png`

### CLI Flags

| Flag | Description |
|------|-------------|
| `--mode image\|mermaid` | Generation mode (default: image) |
| `--root DIR` | Repository root directory |
| `--output PATH` | Output image path |
| `--refresh-architecture` | Force new LLM analysis |
| `--force-image` | Force image regeneration |
| `--hero-style STRING` | Custom style variation (e.g., "more neon") |
| `--skip-readme` | Skip README.md update |

## CI/CD Workflow

The `.github/workflows/generate_art.yml` pipeline triggers on:
- Commits containing `[GEN_ART]` in the message
- Manual workflow dispatch with configurable options

It will:
1. Analyze the code (or use cache)
2. Generate the hero image
3. Commit `assets/architecture_diagram.png` and `assets/architecture.json`

### GitHub Secrets Required

- `GEMINI_API_KEY` – For architecture analysis
- `ARCH_MODEL_NAME` (optional) – Override the default model
