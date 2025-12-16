# Repo-Artist Setup Guide

This guide walks you through setting up Repo-Artist from scratch, including all API keys and cloud configurations.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 minutes)](#quick-start-5-minutes)
3. [Step 1: Get a Gemini API Key (Required)](#step-1-get-a-gemini-api-key-required)
4. [Step 2: Create GitHub OAuth App (Required for Web UI)](#step-2-create-github-oauth-app-required-for-web-ui)
5. [Step 3: Set Up Google Cloud for Imagen 3 (Optional - Premium Images)](#step-3-set-up-google-cloud-for-imagen-3-optional---premium-images)
6. [Step 4: Configure Environment Variables](#step-4-configure-environment-variables)
7. [Step 5: Run the Application](#step-5-run-the-application)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.10+** installed
- **Node.js 18+** installed (for frontend)
- **Git** installed
- A **GitHub account**
- A **Google account** (for Gemini API)

---

## Quick Start (5 minutes)

If you just want to get started quickly with the **free tier** (Pollinations.ai for images):

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/repo-artist.git
cd repo-artist
pip install -r requirements.txt

# 2. Run the setup wizard
python scripts/repo_artist_setup.py
```

The wizard will guide you through creating the necessary API keys.

---

## Step 1: Get a Gemini API Key (Required)

The Gemini API is used for **architecture analysis** - understanding your codebase structure.

### Instructions

1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**

2. Sign in with your Google account

3. Click **"Create API Key"**

   ![Create API Key](https://ai.google.dev/static/images/aistudio-apikey.png)

4. Select or create a Google Cloud project (any project works)

5. **Copy the API key** - it looks like: `AIzaSy...`

6. Save it somewhere safe - you'll need it in Step 4

### Pricing

- **Free tier**: 15 requests/minute, 1 million tokens/month
- More than enough for personal use

---

## Step 2: Create GitHub OAuth App (Required for Web UI)

The GitHub OAuth App allows Repo-Artist to commit images directly to your repositories.

### Instructions

1. Go to **[GitHub Developer Settings](https://github.com/settings/developers)**

2. Click **"OAuth Apps"** in the sidebar

3. Click **"New OAuth App"**

4. Fill in the form:

   | Field | Value |
   |-------|-------|
   | **Application name** | `Repo-Artist` (or any name) |
   | **Homepage URL** | `http://localhost:8000` |
   | **Authorization callback URL** | `http://localhost:8000/auth/callback` |

   ![GitHub OAuth Form](https://docs.github.com/assets/cb-34573/images/help/oauth/oauth-app-form.png)

5. Click **"Register application"**

6. On the next page, you'll see your **Client ID** - copy it

7. Click **"Generate a new client secret"**

8. **Copy the Client Secret** immediately (you won't see it again!)

### What You'll Have

- **Client ID**: `Iv1.abc123...` (public identifier)
- **Client Secret**: `abc123def456...` (keep this secret!)

---

## Step 3: Set Up Google Cloud for Imagen 3 (Optional - Premium Images)

> **Note**: This step is **optional**. Without it, Repo-Artist uses **Pollinations.ai** (free) for image generation, which produces good results. Imagen 3 produces **premium quality** images but requires a Google Cloud account with billing enabled.

### Why Imagen 3?

| Feature | Pollinations.ai (Free) | Imagen 3 (Premium) |
|---------|------------------------|-------------------|
| Quality | Good | Excellent |
| Speed | ~15-20 seconds | ~50 seconds |
| Cost | Free | ~$0.02/image |
| Setup | None | Google Cloud setup |

### Instructions

#### 3.1 Create a Google Cloud Project

1. Go to **[Google Cloud Console](https://console.cloud.google.com/)**

2. Click the project dropdown at the top → **"New Project"**

3. Enter a project name (e.g., `repo-artist`) and click **"Create"**

4. **Note your Project ID** (shown below the name) - you'll need this

#### 3.2 Enable the Vertex AI API

1. In Google Cloud Console, go to **[APIs & Services](https://console.cloud.google.com/apis/library)**

2. Search for **"Vertex AI API"**

3. Click on it and click **"Enable"**

#### 3.3 Enable Billing

> Imagen 3 requires billing to be enabled. You get **$300 free credits** for new accounts.

1. Go to **[Billing](https://console.cloud.google.com/billing)**

2. Link a billing account to your project

3. New accounts get $300 in free credits (valid for 90 days)

#### 3.4 Create a Service Account

1. Go to **[IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)**

2. Click **"Create Service Account"**

3. Fill in:
   - **Name**: `repo-artist-imagen`
   - **Description**: `Service account for Repo-Artist Imagen 3`

4. Click **"Create and Continue"**

5. Grant the role: **"Vertex AI User"**

6. Click **"Done"**

#### 3.5 Create and Download the JSON Key

1. Click on the service account you just created

2. Go to the **"Keys"** tab

3. Click **"Add Key"** → **"Create new key"**

4. Select **"JSON"** and click **"Create"**

5. A JSON file will download - **save it securely!**

6. **Move the file** to a safe location, e.g.:
   ```
   # Windows
   C:\Users\YOUR_NAME\.config\gcloud\repo-artist-key.json
   
   # Mac/Linux
   ~/.config/gcloud/repo-artist-key.json
   ```

#### 3.6 Set the Environment Variable

Add this to your system environment or `.env` file:

```bash
# Point to your JSON key file
GOOGLE_APPLICATION_CREDENTIALS=C:\Users\YOUR_NAME\.config\gcloud\repo-artist-key.json

# Your Google Cloud Project ID
IMAGEN_PROJECT_ID=your-project-id

# Region (us-central1 has best availability)
IMAGEN_LOCATION=us-central1
```

---

## Step 4: Configure Environment Variables

Create a `.env` file in the repo-artist root directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your values:

```env
# ============================================
# REQUIRED
# ============================================

# Gemini API Key (from Step 1)
GEMINI_API_KEY=AIzaSy...your-key-here

# GitHub OAuth (from Step 2)
GITHUB_CLIENT_ID=Iv1.abc123...
GITHUB_CLIENT_SECRET=abc123def456...
GITHUB_REDIRECT_URI=http://localhost:8000/auth/callback

# ============================================
# OPTIONAL - Imagen 3 (from Step 3)
# ============================================

# Uncomment these if you set up Google Cloud
# GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\key.json
# IMAGEN_PROJECT_ID=your-project-id
# IMAGEN_LOCATION=us-central1

# ============================================
# OPTIONAL - Performance Tuning
# ============================================

# Skip Imagen 3 and use faster Pollinations.ai
# IMAGE_TIER=pollinations

# Gemini model for analysis (default: gemini-2.5-flash)
# ARCH_MODEL_NAME=gemini-2.5-flash
```

---

## Step 5: Run the Application

### Option A: Setup Wizard (Recommended)

```bash
python scripts/repo_artist_setup.py
```

This will:
1. Verify your configuration
2. Build the frontend (if needed)
3. Start the server at `http://localhost:8000`

### Option B: Manual Start

```bash
# Build frontend (first time only)
cd web/frontend
npm install
npm run build
cd ../..

# Start server
python -m uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
```

### Option C: CLI Only (No Web UI)

```bash
# Generate architecture image for current directory
python scripts/cli.py generate

# Generate for a specific repo
python scripts/cli.py generate --path /path/to/your/repo
```

---

## Troubleshooting

### "GEMINI_API_KEY is missing"

- Make sure your `.env` file exists and contains `GEMINI_API_KEY=...`
- The key should start with `AIzaSy`

### "Failed to fetch repository structure"

- Check your GitHub OAuth credentials
- Make sure you're logged in via the web UI
- Verify the repository URL is correct and public (or you have access)

### "Port 8000 already in use"

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :8000
kill -9 <PID>
```

### Imagen 3 not working

1. Verify `GOOGLE_APPLICATION_CREDENTIALS` points to a valid JSON file
2. Check that billing is enabled on your Google Cloud project
3. Ensure the Vertex AI API is enabled
4. Verify the service account has "Vertex AI User" role

### Images are slow to generate

Add this to your `.env` to use the faster (free) Pollinations.ai:

```env
IMAGE_TIER=pollinations
```

### "Frontend build not found"

```bash
cd web/frontend
npm install
npm run build
```

---

## Image Generation Tiers

Repo-Artist automatically falls back through these tiers:

| Tier | Service | Quality | Speed | Cost | Setup |
|------|---------|---------|-------|------|-------|
| 1 | Imagen 3 | Excellent | ~50s | ~$0.02 | Google Cloud |
| 2 | Pollinations.ai | Good | ~15s | Free | None |
| 3 | Mermaid | Basic | ~2s | Free | None |

To force a specific tier, set `IMAGE_TIER` in your `.env`:

```env
# Use only Pollinations (skip Imagen 3)
IMAGE_TIER=pollinations

# Use only Imagen 3 (no fallback to Pollinations)
IMAGE_TIER=imagen3

# Auto (default) - try all tiers in order
IMAGE_TIER=auto
```

---

## Next Steps

1. **Try the Web UI**: Open `http://localhost:8000` and generate your first architecture image
2. **Set up CI/CD**: Run `python scripts/cli.py setup-ci` to auto-generate images on push
3. **Customize styles**: Use the Visual Style dropdown in the Web UI
4. **Read the README**: Check out advanced features like `.artistignore` and smart push

---

## Need Help?

- Check the [README.md](../README.md) for more details
- Review the [spec.md](../spec.md) for technical specifications
- Open an issue on GitHub if you're stuck
