import os
import subprocess
import time
import sys

def run_command(command, cwd=None):
    print(f"Running: {command} in {cwd or os.getcwd()}")
    return subprocess.run(command, shell=True, cwd=cwd)

def setup_environment():
    # 1. Install Backend Dependencies
    print("--- Installing Backend Dependencies ---")
    run_command("pip install -r backend/requirements.txt")

    # 2. Install Frontend Dependencies
    print("--- Installing Frontend Dependencies ---")
    run_command("cmd /c npm install", cwd="frontend")

    # 3. Check and Install FFmpeg
    print("--- Checking FFmpeg ---")
    res = subprocess.run("ffmpeg -version", shell=True, capture_output=True)
    if res.returncode != 0:
        print("FFmpeg not found. Attempting install via winget...")
        run_command("winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements")
    else:
        print("FFmpeg is already installed.")

    # 4. Start Docker Infrastructure
    print("--- Starting Docker (PostgreSQL + Temporal) ---")
    run_command("docker-compose up -d")
    
    # Wait for database/temporal to be ready
    print("Waiting for infrastructure to stabilize (10s)...")
    time.sleep(10)

def launch_services():
    print("--- Launching VartaPravah Ecosystem ---")
    
    # In a real environment, we'd use a process manager like PM2 or supervisor
    # For local dev, we'll suggest opening separate terminals for monitoring.
    
    # Opening separate terminal windows for the worker and backend on Windows
    # 1. Temporal Worker
    subprocess.Popen(["start", "cmd", "/k", "python", "-m", "temporal.worker"], shell=True, cwd="backend")
    
    # 2. FastAPI Backend
    subprocess.Popen(["start", "cmd", "/k", "uvicorn", "main:app", "--reload"], shell=True, cwd="backend")
    
    # 3. Next.js Frontend
    subprocess.Popen(["start", "cmd", "/k", "npm", "run", "dev"], shell=True, cwd="frontend")

    print("\nVartaPravah is launching!")
    print("Dashboard: http://localhost:3000/dashboard")
    print("FastAPI: http://localhost:8000/docs")
    print("Temporal UI: http://localhost:8080")

if __name__ == "__main__":
    if "--no-setup" not in sys.argv:
        setup_environment()
    launch_services()
