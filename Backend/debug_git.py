import subprocess
import os

try:
    print("Running git status...")
    res = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=os.getcwd())
    
    print("Running git log -1...")
    res_log = subprocess.run(["git", "log", "-1"], capture_output=True, text=True, cwd=os.getcwd())
    
    with open("git_check.txt", "w") as f:
        f.write("=== GIT STATUS ===\n")
        f.write(res.stdout)
        f.write(res.stderr)
        f.write("\n=== GIT LOG HEAD ===\n")
        f.write(res_log.stdout)
        f.write(res_log.stderr)
        
    print("Files written to git_check.txt")
except Exception as e:
    with open("git_check.txt", "w") as f:
        f.write(f"EXCEPTION: {str(e)}")
