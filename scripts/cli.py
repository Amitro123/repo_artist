#!/usr/bin/env python3
"""
Repo-Artist: Architecture Hero Image Generator

Analyzes a Git repository and generates a sci-fi isometric architecture
hero image that is automatically added to the repo's README.

CLI Tool with subcommands:
    generate: Analyze repo -> generate image -> update README
    setup-ci: Create GitHub Actions workflow

Usage:
    python scripts/cli.py generate [--mode image|mermaid] [--path DIR] [--api-key KEY]
    python scripts/cli.py setup-ci
"""

import os
import sys
import argparse
import shutil
import subprocess
import re
from dotenv import load_dotenv

from repo_artist.core import (
    get_code_context,
    analyze_architecture,
    build_hero_prompt,
    generate_hero_image,
    generate_hero_image_mermaid,
    update_readme_content,
    DEFAULT_MODEL
)
from repo_artist.config import RepoArtistConfig

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
OUTPUT_PATH = "assets/architecture_diagram.png"
ARCHITECTURE_CACHE_PATH = "assets/architecture.json"

def update_readme(image_path="assets/architecture_diagram.png", readme_path="README.md"):
    """Step 5: Ensures README.md contains a reference to the hero image."""
    
    # Ensure directory exists if creating new readme
    os.makedirs(os.path.dirname(os.path.abspath(readme_path)), exist_ok=True)
    
    content = ""
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
    new_content = update_readme_content(content, image_path)
    
    if new_content != content:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ README.md updated")
        return True
    else:
        print("   README.md already up to date")
        return True


def ensure_api_key(args_key):
    """
    Ensures GEMINI_API_KEY is available.
    """
    api_key = args_key or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("\n🔑 GEMINI_API_KEY is missing!")
        print("To generate an architecture diagram, we need a Google Gemini API Key.")
        print("You can get one for free at: https://aistudio.google.com/app/apikey\n")
        
        try:
            api_key = input("Enter your GEMINI_API_KEY: ").strip()
            if api_key:
                save = input("Save this key to .env for future use? [y/N] ").strip().lower()
                if save == 'y':
                    with open(".env", "a") as f:
                        f.write(f"\nGEMINI_API_KEY={api_key}\n")
                    print("✅ Saved to .env")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled.")
            sys.exit(1)
            
    if not api_key:
        print("❌ No API key provided. Cannot proceed with architecture analysis.")
        sys.exit(1)
        
    return api_key


def cmd_generate(args):
    """Main execution entry point for 'generate' command."""
    root_dir = args.path
    
    print("\n" + "=" * 60)
    print("🚀 Repo-Artist: Generation Mode")
    print(f"   Root: {os.path.abspath(root_dir)}")
    print(f"   Mode: {args.mode}")
    print("=" * 60 + "\n")

    # Step 0: Ensure API Key
    api_key = ensure_api_key(args.api_key)

    # Step 1: Harvest repository structure
    structure = get_code_context(root_dir)
    if not structure:
        print("❌ No files found to analyze.")
        sys.exit(1)
    
    print()
    
    # Step 2: Analyze architecture
    cache_path = os.path.join(root_dir, ARCHITECTURE_CACHE_PATH) if root_dir != "." else ARCHITECTURE_CACHE_PATH
    architecture = analyze_architecture(
        structure, 
        api_key=api_key,
        model_name=os.getenv("ARCH_MODEL_NAME", DEFAULT_MODEL),
        force_refresh=args.refresh_architecture,
        cache_path=cache_path
    )
    
    if not architecture:
        print("❌ Failed to analyze architecture.")
        sys.exit(1)
    
    print()
    
    # Step 3 & 4: Generate Image or Diagram
    success = False
    output_full_path = os.path.join(root_dir, args.output)
    
    config = RepoArtistConfig.from_env(root_dir)
    config.force_reanalyze = args.refresh_architecture
    
    if args.mode == "image":
        prompt = build_hero_prompt(architecture, hero_style=args.hero_style)
        if prompt:
            print()
            content = generate_hero_image(prompt, architecture, output_full_path, config)
            success = content is not None
    else:
        content = generate_hero_image_mermaid(architecture, output_full_path)
        success = content is not None
    
    if not success:
        print("❌ Failed to generate hero image.")
        sys.exit(1)
    
    print()
    
    # Step 5: Update README
    if not args.skip_readme:
        readme_full_path = os.path.join(root_dir, "README.md")
        # Relative path for the readme link
        rel_image_path = os.path.relpath(output_full_path, os.path.dirname(readme_full_path) or ".")
        rel_image_path = rel_image_path.replace("\\", "/")
        update_readme(rel_image_path, readme_full_path)
    
    print()
    print("=" * 60)
    print("✅ Repo-Artist Pipeline Complete!")
    print(f"   Output: {output_full_path}")
    print("=" * 60 + "\n")


def cmd_setup_ci(args):
    """Sets up the GitHub Actions workflow."""
    print("\n🤖 Setting up GitHub Actions CI...")
    
    workflow_content = """name: Repo-Artist Logic

on:
  push:
    paths-ignore:
      - 'assets/**'
      - 'README.md'
  workflow_dispatch:
    inputs:
      force_refresh:
        description: 'Force new architecture analysis'
        required: false
        type: boolean
        default: false
      hero_style:
        description: 'Style variation (e.g. "cyberpunk", "minimal")'
        required: false
        type: string

permissions:
  contents: write

jobs:
  generate-art:
    if: "contains(github.event.head_commit.message, '[GEN_ART]') || github.event_name == 'workflow_dispatch'"
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install Dependencies
        run: |
          pip install requests google-generativeai python-dotenv
          # Ensure repo_artist package is available
          export PYTHONPATH=$PYTHONPATH:.
          
      - name: Generate Hero Image
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          ARCH_MODEL_NAME: ${{ secrets.ARCH_MODEL_NAME || 'gemini-2.5-flash' }}
          REFRESH_ARCHITECTURE: ${{ inputs.force_refresh }}
          HERO_STYLE: ${{ inputs.hero_style }}
        run: |
          python scripts/repo_artist.py generate --api-key "$GEMINI_API_KEY" --hero-style "$HERO_STYLE"
          
      - name: Commit & Push
        run: |
          git config --global user.name "Repo-Artist Bot"
          git config --global user.email "bot@repo-artist.com"
          git add assets/ README.md
          git commit -m "🤖 [Repo-Artist] Updated architecture hero image" || echo "No changes to commit"
          git push
"""
    
    target_dir = os.path.join(".github", "workflows")
    target_file = os.path.join(target_dir, "generate_art.yml")
    
    os.makedirs(target_dir, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(workflow_content)
        
    print(f"✅ Created workflow file: {target_file}")
    
    # Check for gh CLI
    if shutil.which("gh"):
        print("\n👀 GitHub CLI (gh) detected.")
        choice = input("Do you want to upload GEMINI_API_KEY to GitHub Secrets now? [y/N] ").strip().lower()
        if choice == 'y':
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                api_key = input("Enter GEMINI_API_KEY: ").strip()
            
            if api_key:
                print("⏳ Uploading secret...")
                try:
                    subprocess.run(
                        ["gh", "secret", "set", "GEMINI_API_KEY", "--body", api_key],
                        check=True
                    )
                    print("✅ Secret GEMINI_API_KEY set successfully!")
                except subprocess.CalledProcessError:
                    print("❌ Failed to set secret via gh CLI. Please set it manually in GitHub Settings.")
            else:
                print("⚠️ No key provided, skipping secret upload.")
    else:
        print("\nℹ️ To enable CI, go to your Repo Settings -> Secrets and add GEMINI_API_KEY.")
    
    print("\n✅ Setup complete! Push your code to enable the workflow.")


def main():
    parser = argparse.ArgumentParser(
        description="Repo-Artist: Automated Architecture Hero Image Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")
    
    # --- GENERATE COMMAND ---
    p_gen = subparsers.add_parser("generate", help="Analyze repo and generate hero image")
    p_gen.add_argument("--path", default=".", help="Path to target repository (default: current)")
    p_gen.add_argument("--mode", default="image", choices=["image", "mermaid"], help="Generation mode")
    p_gen.add_argument("--api-key", help="Gemini API Key (overrides env var)")
    p_gen.add_argument("--output", default=OUTPUT_PATH, help="Output image path")
    p_gen.add_argument("--hero-style", help="Style variation for image prompt")
    p_gen.add_argument("--refresh-architecture", action="store_true", help="Force new LLM analysis")
    p_gen.add_argument("--skip-readme", action="store_true", help="Skip updating README.md")
    p_gen.set_defaults(func=cmd_generate)
    
    # --- SETUP-CI COMMAND ---
    p_setup = subparsers.add_parser("setup-ci", help="Configure GitHub Actions workflow")
    p_setup.set_defaults(func=cmd_setup_ci)
    
    # Parse and Run
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
