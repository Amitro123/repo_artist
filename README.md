# Repo-Artist


![Architecture](./assets/architecture_diagram.png)

**Automated Architecture Hero Image Generator for GitHub Repositories.**

Repo-Artist analyzes your codebase using **Google Gemini** to understand your architecture, then generates a high-end, sci-fi isometric "Hero Image" for your project.

![Architecture](assetsrchitecture_diagram.png)

## Features

- **AI-Powered Analysis**: Uses Gemini to analyze your code structure and infer architecture components.
- **Interactive Refinement**: Modify generated images using natural language (e.g., "Make the database red", "Add cloud icons").
- **Persistent Architecture Caching**: Saves architecture analysis to `repo-artist-architecture.json` for faster subsequent runs.
- **Smart Caching**: `architecture.json` and `architecture_diagram.png` are cached to avoid unnecessary LLM calls and image regeneration.
- **Configurable Model**: Choose which Gemini model to use via environment variable.
- **Smart Detection**: Only generates new art when significant changes are detected (> 3 files or > 50 lines).
- **CI Integration**: Runs on `git push` via GitHub Actions when `[GEN_ART]` tag is present.

## Installation

1. Clone the repository.
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Web App & Setup

The easiest way to get started is the **Setup Wizard**, which configuring your keys and launches the Web UI.

1. **Run the Setup Wizard**:
   ```bash
   python scripts/repo_artist_setup.py
   ```
2. **Follow the Prompts**:
   - It will guide you to create a **GitHub OAuth App** (required for the web interface).
   - Enter your Client ID, Client Secret, and Gemini API Key.
   - It will automatically save them to `.env` and start the server.

3. **Use the Web App**:
   - **Preview**: Enter a Repo URL to see the architecture hero image.
   - **Refine**: Use natural language to modify the image ("Make it more colorful", "Add cloud icons").
   - **View Tabs**: Switch between Preview (rendered README), Code (raw markdown), and Architecture JSON (analyzed data).
   - **Apply**: Click to commit the image and README update directly to GitHub.

### GUI Preview

![Repo-Artist UI](assets/app_screenshot.png)


## CLI Usage (Recommended)

The easiest way to use Repo-Artist is via the CLI. There is no need to manually edit files.

```bash
# 1. Generate Architecture Diagram
python scripts/cli.py generate

# If GEMINI_API_KEY is missing, the tool will ask for it interactively
# and offer to save it to your .env file.
```

### Options

```bash
# Point to a different repo
python scripts/cli.py generate --path /path/to/other/repo

# Use Mermaid diagrams (no image generation, just structure)
python scripts/cli.py generate --mode mermaid

# Force refresh of the architecture analysis (ignore cache)
python scripts/cli.py generate --refresh-architecture

# Custom style variation
python scripts/cli.py generate --hero-style "cyberpunk neon"
```

### 🤝 GitHub Actions / CI (Advanced)

To enable automatic updates on `git push`, set up the GitHub Action:

```bash
python scripts/cli.py setup-ci
```

This command will:
1. Create `.github/workflows/generate_art.yml`
2. Automatically detect `gh` CLI and offer to upload your `GEMINI_API_KEY` to GitHub Secrets.

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google AI API key for architecture analysis |
| `ARCH_MODEL_NAME` | No | `gemini-2.5-flash` | Gemini model to use for analysis |
| `IMAGEN_PROJECT_ID` | No | - | Google Cloud project ID for Imagen 3 (Tier 1 image generation) |
| `IMAGEN_LOCATION` | No | `us-central1` | Google Cloud location for Imagen 3 |
| `REPO_ARTIST_MAX_DEPTH` | No | `3` | Maximum directory depth to scan |
| `REPO_ARTIST_MAX_COMPONENTS` | No | `7` | Maximum components to include in prompt |
| `REPO_ARTIST_MAX_CONNECTIONS` | No | `7` | Maximum connections to include in prompt |
| `REPO_ARTIST_OUTPUT_DIR` | No | `assets` | Output directory for generated images |

### Caching

- **Persistent Architecture JSON**: `repo-artist-architecture.json` – Saved in repository root, reused across runs
- **Local Architecture cache**: `assets/architecture.json` – Stores the analyzed architecture JSON
- **Image cache**: `assets/architecture_diagram.png` – Generated hero image

To bypass caching:
- **Web UI**: Check "Force re-analyze (ignore cached architecture)" checkbox
- **CLI**: `--refresh-architecture` – Forces new LLM analysis AND new image generation (skips cache)

### Custom Ignore Patterns

Create a `.artistignore` file in your repository root to customize which directories are excluded from analysis:

```
# Example .artistignore
vendor
third_party
legacy_code
```

### Image Generation Tiers

Repo-Artist uses a multi-tier fallback strategy for image generation:

1. **Tier 1 (Premium)**: Google Imagen 3 via Vertex AI - Requires `IMAGEN_PROJECT_ID` and `google-cloud-aiplatform` package
2. **Tier 2 (Free)**: Pollinations.ai - Free, no configuration needed
3. **Tier 3 (Fallback)**: Mermaid diagram - Always available as last resort

## Testing

Repo-Artist includes a comprehensive test suite with **54 tests** covering all major functionality:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v
pytest tests/test_core_logic.py -v
pytest tests/test_image_generation.py -v
```

**Test Coverage:**
- ✅ Configuration system (10 tests) - env vars, .artistignore, path generation
- ✅ Core logic (30 tests) - code context, JSON retry, prompt building, README updates, caching
- ✅ Image generation (14 tests) - multi-tier fallback, retry mechanisms, error handling

All tests pass successfully with 100% coverage of critical paths.

## Advanced Usage

### Local Trigger via Smart Push

Use the wrapper script to conditionally trigger generation before pushing:

```bash
python smart_push.py origin main
```

If significant changes are detected, it will offer options to refresh the art before pushing.
