import subprocess
import sys

def run_command(command):
    """Runs a shell command and returns output."""
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(e.stderr)
        sys.exit(1)

def get_git_changes():
    """Gets the diff stats from git."""
    # Ensure ignore space change or blank lines doesn't affect the count if strictly "lines changed" matters, 
    # but --shortstat usually handles this well.
    # checking against origin/main assuming we are on main or a feature branch pushing to main
    # Ideally should check against the upstream tracking branch.
    try:
        # Check if there is an upstream configured
        upstream = run_command("git rev-parse --abbrev-ref --symbolic-full-name @{u}")
    except:
        # Verification fallback or no upstream
        print("No upstream branch found. Assuming first push or local testing.")
        return 0, 0

    cmd = f"git diff --shortstat {upstream} HEAD"
    output = run_command(cmd)
    
    # Output format example: " 3 files changed, 10 insertions(+), 5 deletions(-)"
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
    print("Checking for architecture changes...")
    files, lines = get_git_changes()
    print(f"Detected: {files} files changed, {lines} lines changed.")

    if files > 3 or lines > 50:
        response = input("Architecture changes detected. Generate new Art? [y/N]: ").strip().lower()
        if response == 'y':
            print("Triggering art generation...")
            run_command("git commit --allow-empty -m \"[GEN_ART] Triggering architecture update\"")
            
    # Executing the actual git push
    # Pass through any arguments provided to this script
    args = " ".join(sys.argv[1:])
    print(f"Pushing to remote... (git push {args})")
    
    # We use subprocess.call to allow it to be interactive if needed (though push usually isn't unless creds needed)
    ret = subprocess.call(f"git push {args}", shell=True)
    sys.exit(ret)

if __name__ == "__main__":
    main()
