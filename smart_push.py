#!/usr/bin/env python3
"""
Smart Push: Git wrapper that detects significant changes and triggers art generation.

When pushing commits with significant code changes, this script asks the user
whether to generate new architecture art. If confirmed, it creates a commit
with the [GEN_ART] marker that triggers the GitHub Actions workflow.

Usage:
    python smart_push.py [git push arguments...]
    
Example:
    python smart_push.py origin main
"""

import subprocess
import sys


def run_command(command, check=True):
    """Runs a shell command and returns output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=check, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Error running command: {command}")
            print(e.stderr)
            sys.exit(1)
        return ""


def get_git_changes():
    """Gets the diff stats from git."""
    try:
        upstream = run_command("git rev-parse --abbrev-ref --symbolic-full-name @{u}", check=False)
        if not upstream:
            print("ℹ️ No upstream branch found. Assuming first push.")
            return 0, 0
    except:
        print("ℹ️ No upstream branch found. Assuming first push or local testing.")
        return 0, 0

    cmd = f"git diff --shortstat {upstream} HEAD"
    output = run_command(cmd, check=False)
    
    if not output:
        return 0, 0

    parts = output.split(',')
    files_changed = 0
    lines_changed = 0

    for part in parts:
        part = part.strip()
        if "file" in part:
            files_changed = int(part.split()[0])
        elif "insertion" in part:
            lines_changed += int(part.split()[0])
        elif "deletion" in part:
            lines_changed += int(part.split()[0])
            
    return files_changed, lines_changed


def main():
    print("\n🔍 Smart Push: Checking for architecture changes...\n")
    
    files, lines = get_git_changes()
    print(f"   Detected: {files} files changed, {lines} lines changed.\n")

    # Threshold for significant changes
    if files > 3 or lines > 50:
        print("=" * 50)
        print("📊 Significant changes detected!")
        print("=" * 50)
        
        # First question: Generate new art?
        response = input("\n🎨 Architecture changes detected. Generate new Art? [y/N]: ").strip().lower()
        
        if response == 'y':
            # Second question: Reuse architecture or regenerate?
            print("\n📦 Options:")
            print("   1. Full refresh (new architecture analysis + new image)")
            print("   2. Reuse cached architecture, regenerate image only")
            print("   3. Cancel")
            
            choice = input("\nChoice [1/2/3]: ").strip()
            
            if choice == '1':
                # Full refresh: [GEN_ART] with refresh flags
                print("\n🔄 Creating commit to trigger full architecture refresh...")
                run_command('git commit --allow-empty -m "[GEN_ART] Refresh architecture and regenerate hero image"')
                print("✅ Created [GEN_ART] commit for full refresh")
                
            elif choice == '2':
                # Reuse architecture, force image
                print("\n🔄 Creating commit to regenerate image only...")
                run_command('git commit --allow-empty -m "[GEN_ART] Regenerate hero image from cached architecture"')
                print("✅ Created [GEN_ART] commit for image regeneration")
                
            else:
                print("\n⏭️ Skipping art generation.")
        else:
            print("\n⏭️ Skipping art generation.")
    else:
        print("ℹ️ Changes below threshold. No art generation needed.")
    
    # Execute the actual git push
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    print(f"\n📤 Pushing to remote... (git push {args})")
    
    ret = subprocess.call(f"git push {args}", shell=True)
    
    if ret == 0:
        print("\n✅ Push complete!")
    else:
        print(f"\n❌ Push failed with exit code {ret}")
    
    sys.exit(ret)


if __name__ == "__main__":
    main()
