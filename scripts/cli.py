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
import getpass
from importlib import resources
from dotenv import load_dotenv

# Rich library for consistent, professional UX
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table

from repo_artist.core import (
    get_code_context,
    analyze_architecture,
    build_hero_prompt,
    generate_hero_image,
    generate_hero_image_mermaid,
    update_readme_content,
)
from repo_artist.config import RepoArtistConfig, DEFAULT_MODEL

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

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
        console.print("[bold green]✅ README.md updated[/bold green]")
        return True
    else:
        console.print("[dim]   README.md already up to date[/dim]")
        return True


def ensure_api_key(args_key):
    """
    Ensures GEMINI_API_KEY is available.
    Uses Rich for consistent UX with secure password input.
    """
    api_key = args_key or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        console.print(Panel(
            "[bold yellow]🔑 GEMINI_API_KEY is missing![/bold yellow]\n\n"
            "To generate an architecture diagram, we need a Google Gemini API Key.\n"
            "Get one for free at: [link=https://aistudio.google.com/app/apikey]https://aistudio.google.com/app/apikey[/link]",
            title="API Key Required",
            border_style="yellow"
        ))
        
        try:
            api_key = Prompt.ask("[cyan]Enter your GEMINI_API_KEY[/cyan]", password=True).strip()
            if api_key:
                if Confirm.ask("Save this key to .env for future use?", default=False):
                    with open(".env", "a") as f:
                        f.write(f"\nGEMINI_API_KEY={api_key}\n")
                    console.print("[bold green]✅ Saved to .env[/bold green]")
        except KeyboardInterrupt:
            console.print("\n[bold red]❌ Operation cancelled.[/bold red]")
            sys.exit(1)
            
    if not api_key:
        console.print("[bold red]❌ No API key provided. Cannot proceed with architecture analysis.[/bold red]")
        sys.exit(1)
        
    return api_key


def cmd_generate(args):
    """Main execution entry point for 'generate' command."""
    root_dir = args.path
    
    # Display header with Rich
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_row("[bold]Root:[/bold]", f"[cyan]{os.path.abspath(root_dir)}[/cyan]")
    info_table.add_row("[bold]Mode:[/bold]", f"[cyan]{args.mode}[/cyan]")
    
    console.print(Panel(
        info_table,
        title="[bold cyan]🚀 Repo-Artist: Generation Mode[/bold cyan]",
        border_style="cyan"
    ))

    # Step 0: Ensure API Key
    api_key = ensure_api_key(args.api_key)

    # Step 1: Harvest repository structure
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
        progress.add_task(description="Harvesting project structure...", total=None)
        structure = get_code_context(root_dir)
    
    if not structure:
        console.print("[bold red]❌ No files found to analyze.[/bold red]")
        sys.exit(1)
    
    console.print("[green]✅ Project structure harvested[/green]")
    
    # Step 2: Analyze architecture
    cache_path = os.path.join(root_dir, ARCHITECTURE_CACHE_PATH) if root_dir != "." else ARCHITECTURE_CACHE_PATH
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
        progress.add_task(description="Analyzing architecture with Gemini...", total=None)
        architecture = analyze_architecture(
            structure, 
            api_key=api_key,
            model_name=os.getenv("ARCH_MODEL_NAME", DEFAULT_MODEL),
            force_refresh=args.refresh_architecture,
            cache_path=cache_path
        )
    
    if not architecture:
        console.print("[bold red]❌ Failed to analyze architecture.[/bold red]")
        sys.exit(1)
    
    console.print(f"[green]✅ Architecture analyzed: {len(architecture.get('components', []))} components[/green]")
    
    # Step 3 & 4: Generate Image or Diagram
    success = False
    output_full_path = os.path.join(root_dir, args.output)
    
    config = RepoArtistConfig.from_env(root_dir)
    config.force_reanalyze = args.refresh_architecture
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
        progress.add_task(description="Generating hero image...", total=None)
        
        if args.mode == "image":
            prompt = build_hero_prompt(architecture, hero_style=args.hero_style)
            if prompt:
                content = generate_hero_image(prompt, architecture, output_full_path, config)
                success = content is not None
        else:
            content = generate_hero_image_mermaid(architecture, output_full_path)
            success = content is not None
    
    if not success:
        console.print("[bold red]❌ Failed to generate hero image.[/bold red]")
        sys.exit(1)
    
    console.print("[green]✅ Hero image generated[/green]")
    
    # Step 5: Update README
    if not args.skip_readme:
        readme_full_path = os.path.join(root_dir, "README.md")
        # Relative path for the readme link
        rel_image_path = os.path.relpath(output_full_path, os.path.dirname(readme_full_path) or ".")
        rel_image_path = rel_image_path.replace("\\", "/")
        update_readme(rel_image_path, readme_full_path)
    
    # Success panel
    console.print(Panel(
        f"[bold green]✅ Pipeline Complete![/bold green]\n\nOutput: [cyan]{output_full_path}[/cyan]",
        title="[bold green]Repo-Artist[/bold green]",
        border_style="green"
    ))


def _get_template_path() -> str:
    """
    Get the path to the workflow template using importlib.resources for robust access.
    Falls back to relative path if importlib.resources fails.
    """
    # Try importlib.resources first (works with installed packages)
    try:
        # Python 3.9+ style
        if hasattr(resources, 'files'):
            template_files = resources.files('templates')
            template_path = template_files.joinpath('generate_art.yml')
            if hasattr(template_path, 'read_text'):
                # Return the path if it exists
                return str(template_path)
    except (ModuleNotFoundError, TypeError, AttributeError):
        pass
    
    # Fallback to relative path (works when running from source)
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "generate_art.yml")


def cmd_setup_ci(args):
    """Sets up the GitHub Actions workflow with Rich UI."""
    console.print(Panel(
        "[bold cyan]🤖 Setting up GitHub Actions CI...[/bold cyan]",
        border_style="cyan"
    ))
    
    # Load template from file using robust path resolution
    template_path = _get_template_path()
    
    if not os.path.exists(template_path):
        console.print(f"[bold red]❌ Template file not found at {template_path}[/bold red]")
        console.print("[dim]   Please ensure the templates directory exists with generate_art.yml[/dim]")
        sys.exit(1)
    
    with open(template_path, 'r', encoding='utf-8') as f:
        workflow_content = f.read()
    console.print(f"[dim]   Loaded template from {template_path}[/dim]")
    
    target_dir = os.path.join(".github", "workflows")
    target_file = os.path.join(target_dir, "generate_art.yml")
    
    os.makedirs(target_dir, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(workflow_content)
        
    console.print(f"[bold green]✅ Created workflow file: {target_file}[/bold green]")
    
    # Check for gh CLI
    if shutil.which("gh"):
        console.print("\n[bold]👀 GitHub CLI (gh) detected.[/bold]")
        if Confirm.ask("Do you want to upload GEMINI_API_KEY to GitHub Secrets now?", default=False):
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                api_key = Prompt.ask("[cyan]Enter GEMINI_API_KEY[/cyan]", password=True).strip()
            
            if api_key:
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                    progress.add_task(description="Uploading secret...", total=None)
                    try:
                        subprocess.run(
                            ["gh", "secret", "set", "GEMINI_API_KEY", "--body", api_key],
                            check=True,
                            capture_output=True
                        )
                        console.print("[bold green]✅ Secret GEMINI_API_KEY set successfully![/bold green]")
                    except subprocess.CalledProcessError:
                        console.print("[bold red]❌ Failed to set secret via gh CLI. Please set it manually in GitHub Settings.[/bold red]")
            else:
                console.print("[yellow]⚠️ No key provided, skipping secret upload.[/yellow]")
    else:
        console.print("\n[dim]ℹ️ To enable CI, go to your Repo Settings -> Secrets and add GEMINI_API_KEY.[/dim]")
    
    console.print(Panel(
        "[bold green]✅ Setup complete![/bold green]\n\nPush your code to enable the workflow.",
        border_style="green"
    ))


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
