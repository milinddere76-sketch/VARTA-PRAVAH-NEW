import os
import subprocess
import time
import sys
import platform

# ---------------------------
# RUN COMMAND SAFELY
# ---------------------------
def run_command(command, cwd=None):
    print(f"\n🚀 Running: {command}")
    try:
        result = subprocess.run(command, shell=True, cwd=cwd)
        if result.returncode != 0:
            print(f"❌ Command failed: {command}")
            sys.exit(1)
        return result
    except Exception as e:
        print(f"❌ Error running command: {e}")
        sys.exit(1)


# ---------------------------
# DETECT OS
# ---------------------------
IS_WINDOWS = platform.system() == "Windows"


# ---------------------------
# SETUP ENVIRONMENT
# ---------------------------
def setup_environment():
    # Check folders
    if not os.path.exists("backend"):
        print("❌ backend folder not found")
        sys.exit(1)

    if not os.path.exists("frontend"):
        print("❌ frontend folder not found")
        sys.exit(1)

    # -----------------------
    # Backend Dependencies
    # -----------------------
    print("\n--- Installing Backend Dependencies ---")
    run_command("pip install --upgrade -r requirements.txt", cwd="backend")

    # -----------------------
    # Frontend Dependencies
    # -----------------------
    print("\n--- Installing Frontend Dependencies ---")
    run_command("npm install", cwd="frontend")

    # -----------------------
    # FFmpeg Check
    # -----------------------
    print("\n--- Checking FFmpeg ---")
    res = subprocess.run("ffmpeg -version", shell=True, capture_output=True)

    if res.returncode != 0:
        print("⚠️ FFmpeg not found.")
        if IS_WINDOWS:
            print("Installing via winget...")
            run_command("winget install --id=Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements")
        else:
            print("Installing via apt...")
            run_command("sudo apt update && sudo apt install -y ffmpeg")
    else:
        print("✅ FFmpeg already installed")


# ---------------------------
# DOCKER INFRASTRUCTURE
# ---------------------------
def start_infrastructure():
    print("\n--- Starting Docker Infrastructure (Postgres/Temporal) ---")
    docker_cmd = "docker compose"
    result = subprocess.run(f"{docker_cmd} version", shell=True, capture_output=True)
    if result.returncode != 0:
        docker_cmd = "docker-compose"
    
    # We only start the infrastructure services (Postgres and Temporal)
    # The app services (backend, worker, frontend) are run locally by this launcher
    run_command(f"{docker_cmd} up -d postgres temporal temporal-ui")
    
    print("⏳ Waiting for infrastructure to stabilize (15s)...")
    time.sleep(15)


# ---------------------------
# LAUNCH SERVICES
# ---------------------------
def launch_services():
    print("\n--- Launching VartaPravah Ecosystem ---")

    if IS_WINDOWS:
        # Windows terminals (opened in separate Persistent CLI windows)
        subprocess.Popen('start cmd /k "python -m streaming_engine.worker"', shell=True, cwd="backend")
        subprocess.Popen('start cmd /k "uvicorn main:app --reload --host 127.0.0.1 --port 8000"', shell=True, cwd="backend")
        subprocess.Popen('start cmd /k "npm run dev"', shell=True, cwd="frontend")
    else:
        # Linux / Mac (background processes)
        subprocess.Popen(["python", "-m", "streaming_engine.worker"], cwd="backend")
        subprocess.Popen(["uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], cwd="backend")
        subprocess.Popen(["npm", "run", "dev"], cwd="frontend")

    print("\n🎉 VartaPravah is launching!")
    print("🌐 Dashboard: http://localhost:3000/dashboard")
    print("⚙️ FastAPI: http://localhost:8000/docs")
    print("📡 Temporal UI: http://localhost:8088")


# ---------------------------
# ENTRY POINT
# ---------------------------
if __name__ == "__main__":
    if "--no-setup" not in sys.argv:
        setup_environment()
    
    # Infrastructure must ALWAYS be up before we launch
    start_infrastructure()

    launch_services()