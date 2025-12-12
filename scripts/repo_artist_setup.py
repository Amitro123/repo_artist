#!/usr/bin/env python3
"""
Repo-Artist Setup Wizard

Interactive CLI to configure the environment and start the web application.
Powered by Rich for a futuristic terminal experience.
"""

import os
import sys
import webbrowser
import subprocess
import time
from pathlib import Path
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.align import Align
from rich.layout import Layout
from rich.table import Table

console = Console()

def print_header():
    console.clear()
    title = """[bold cyan]
    ██████╗ ███████╗██████╗  ██████╗         █████╗ ██████╗ ████████╗██╗███████╗████████╗
    ██╔══██╗██╔════╝██╔══██╗██╔═══██╗       ██╔══██╗██╔══██╗╚══██╔══╝██║██╔════╝╚══██╔══╝
    ██████╔╝█████╗  ██████╔╝██║   ██║█████╗ ███████║██████╔╝   ██║   ██║███████╗   ██║   
    ██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║╚════╝ ██╔══██║██╔══██╗   ██║   ██║╚════██║   ██║   
    ██║  ██║███████╗██║     ╚██████╔╝       ██║  ██║██║  ██║   ██║   ██║███████║   ██║   
    ╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝        ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝╚══════╝   ╚═╝   
    [/bold cyan] [bold purple]v2.0 // SETUP WIZARD[/bold purple]"""
    
    panel = Panel(
        Align.center(title),
        border_style="cyan",
        subtitle="[dim]Turn Code into Art[/dim]"
    )
    print(panel)

def check_env_file():
    env_path = Path(".env")
    if env_path.exists():
        console.print(Panel("[green]✅ Found existing configuration (.env)[/green]", border_style="green"))
        return True
    else:
        console.print(Panel("[yellow]⚠️  No configuration found. Initiating setup sequence...[/yellow]", border_style="yellow"))
        return False

def load_env_vars():
    vars = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    vars[key.strip()] = val.strip()
    return vars

def update_env_file(new_vars):
    current_vars = load_env_vars()
    current_vars.update(new_vars)
    
    with open(".env", "w") as f:
        for key, val in current_vars.items():
            f.write(f"{key}={val}\n")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Saving configuration...", total=None)
        time.sleep(0.8)
        
    console.print("[bold green]✅ Configuration saved successfully.[/bold green]")

def setup_github_oauth(current_vars):
    console.print("\n[bold cyan]>> PHASE 1: NEURAL UPLINK (GitHub OAuth)[/bold cyan]")
    
    if "GITHUB_CLIENT_ID" in current_vars and "GITHUB_CLIENT_SECRET" in current_vars:
        console.print("[dim]Credentials detected in memory.[/dim]")
        if not Confirm.ask("Do you want to re-configure GitHub OAuth?"):
            return {}

    info = Table(show_header=False, box=None)
    info.add_row("[bold]1. Portal:[/bold]", "[link=https://github.com/settings/developers]https://github.com/settings/developers[/link]")
    info.add_row("[bold]2. Action:[/bold]", "New OAuth App")
    info.add_row("[bold]3. Name:[/bold]", "Repo-Artist Local")
    info.add_row("[bold]4. Homepage:[/bold]", "http://localhost:8000")
    info.add_row("[bold]5. Callback:[/bold]", "http://localhost:8000/auth/callback")
    
    console.print(Panel(info, title="GitHub App Requirements", border_style="blue"))
    
    if Confirm.ask("Open GitHub Developer Settings now?"):
        webbrowser.open("https://github.com/settings/developers")
    
    console.print("\n[bold]Enter obtained credentials:[/bold]")
    client_id = Prompt.ask("[cyan]Client ID[/cyan]")
    client_secret = Prompt.ask("[cyan]Client Secret[/cyan]", password=True)
    
    return {
        "GITHUB_CLIENT_ID": client_id,
        "GITHUB_CLIENT_SECRET": client_secret
    }

def setup_gemini_api(current_vars):
    console.print("\n[bold cyan]>> PHASE 2: CORE INTELLIGENCE (Gemini API)[/bold cyan]")
    
    if "GEMINI_API_KEY" in current_vars:
        console.print("[dim]API Key detected in memory.[/dim]")
        if not Confirm.ask("Do you want to update the API Key?"):
            return {}

    console.print("Generate key at: [link=https://aistudio.google.com/app/apikey]https://aistudio.google.com/app/apikey[/link]")
    
    api_key = Prompt.ask("[cyan]Gemini API Key[/cyan]", password=True)
    return {"GEMINI_API_KEY": api_key}

def final_actions():
    console.print("\n[bold cyan]>> PHASE 3: LAUNCH SEQUENCE[/bold cyan]")
    console.print(Panel("[bold green]System Ready. All parameters nominal.[/bold green]", border_style="green"))
    
    if Confirm.ask("[bold white on green] Start Repo-Artist Server? [/bold white on green]", default=True):
        console.clear()
        console.print("[bold cyan]🚀 Initializing Core Systems...[/bold cyan]")
        console.print("[dim]Press Ctrl+C to abort[/dim]\n")
        
        cmd = [sys.executable, "-m", "uvicorn", "web.backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
        
        try:
             import threading
             def open_url():
                 time.sleep(2)
                 console.print("[bold green]🌍 Uplink established: http://localhost:8000[/bold green]")
                 webbrowser.open("http://localhost:8000")
             
             t = threading.Thread(target=open_url)
             t.daemon = True
             t.start()
             
             subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n[bold red]🛑 System Shutdown Initiated.[/bold red]")

def main():
    print_header()
    check_env_file()
    
    current_vars = load_env_vars()
    updates = {}
    
    updates.update(setup_github_oauth(current_vars))
    updates.update(setup_gemini_api(current_vars))
    
    if updates:
        update_env_file(updates)
    else:
        console.print("[dim]No configuration changes required.[/dim]")
        
    final_actions()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]❌ Manual Override. Setup Aborted.[/bold red]")
        sys.exit(0)
