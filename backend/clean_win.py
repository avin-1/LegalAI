import subprocess
import os
import sys

def run(cmd):
    print(f"Running: {cmd}", flush=True)
    try:
        # We use shell=True to simplify command string handling on Windows for filter-branch
        # But for filter-branch list args are better?
        # Let's use list args.
        
        env = os.environ.copy()
        env["FILTER_BRANCH_SQUELCH_WARNING"] = "1"

        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            env=env,
            shell=True if isinstance(cmd, str) else False
        )
        
        for line in process.stdout:
            print(line, end='', flush=True)
            
        process.wait()
        return process.returncode == 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        return False

print("Starting cleanup...", flush=True)

# 1. Filter Branch
# Note: Using string for command to handle quoting naturally in shell
cmd_filter = 'git filter-branch --force --index-filter "git rm --cached --ignore-unmatch -r .history" --prune-empty --tag-name-filter cat -- --all'
if run(cmd_filter):
    print("Filter branch successful.", flush=True)
    
    # 2. Push
    print("Pushing...", flush=True)
    if run(["git", "push", "origin", "main", "--force"]):
        print("Push successful!", flush=True)
    else:
        print("Push failed.", flush=True)
else:
    print("Filter branch failed.", flush=True)
