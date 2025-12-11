# Repo-Artist

**Automated Architecture Art Generator for GitHub Repositories.**

Repo-Artist analyzes your codebase using **Google Gemini 1.5 Flash** to understand your architecture, and then uses **Stable Diffusion XL** (via Hugging Face) to generate a high-end, Sci-Fi isometric "Hero Image" for your project.

![Repo-Artist Architecture](assets/architecture_diagram.png)

## Features

- **Smart Detection**: Only generates new art when significant changes are detected (> 3 files or > 50 lines changed).
- **AI Analysis**: Reads your code structure (Python, JS, Go, etc.) to understand what you are building.
- **High-Quality Art**: Uses a custom-engineered prompt for "Hyper-Realistic 3D Isometric" aesthetics with volumetric lighting and glass structures.
- **Automated**: Runs on `git push` via a local wrapper or GitHub Actions.

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up Environment Variables:
    - Copy `.env.example` to `.env`:
      ```bash
      cp .env.example .env
      ```
    - Fill in your keys in `.env`:
      - `GEMINI_API_KEY`: Get from [Google AI Studio](https://aistudio.google.com/app/apikey).
      - `HF_TOKEN`: Get from [Hugging Face](https://huggingface.co/settings/tokens).

## Usage

### Local Trigger (Recommended)

Use the wrapper script instead of `git push` to automatically check for architecture changes.

```bash
# Instead of `git push origin main`
python smart_push.py origin main
```

If significant changes are detected, it will ask:
`Architecture changes detected. Generate new Art? [y/N]`

If you say **Yes**, it creates an empty commit that triggers the GitHub Action.

### Manual Generation

You can run the artist manually:

```bash
python scripts/repo_artist.py
```

## Configuration

Top of `scripts/repo_artist.py`:
- `STYLE_TEMPLATE`: Modify this string to change the visual aesthetic of the generated image.
- `EXTENSIONS`: Add or remove file extensions to scan.

## CI/CD Workflow

The `.github/workflows/generate_art.yml` pipeline listens for commits with `[GEN_ART]`. It will:
1.  Analyze the code.
2.  Generate the image.
3.  Commit `assets/architecture_diagram.png` back to the repository.
