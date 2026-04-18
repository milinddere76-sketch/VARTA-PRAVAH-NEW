import time
import subprocess
import os
import glob
import sys

# --- CONFIGURATION ---
MAX_FILES = 5
VIDEOS_DIR = "/app/videos"

def run_background(cmd):
    """Launches a command in the background."""
    print(f"🚀 [AUTO-HEAL] Launching: {cmd}", flush=True)
    subprocess.Popen(cmd, shell=True, start_new_session=True)

def is_alive(name_pattern):
    """Checks if a process matching the pattern is running, excluding the current process."""
    my_pid = os.getpid()
    try:
        output = subprocess.check_output(["pgrep", "-f", name_pattern]).decode().split()
        pids = [int(p) for p in output if int(p) != my_pid]
        return len(pids) > 0
    except subprocess.CalledProcessError:
        return False

def cleanup_storage():
    """Keeps disk usage in check."""
    try:
        files = sorted(glob.glob(os.path.join(VIDEOS_DIR, "news_*.mp4")), key=os.path.getctime)
        if len(files) > MAX_FILES:
            to_delete = files[:-MAX_FILES]
            print(f"🧹 [MONITOR] Cleaning up {len(to_delete)} old videos.", flush=True)
            for f in to_delete:
                try: os.remove(f)
                except: pass
    except Exception as e:
        print(f"⚠️ [MONITOR] Cleanup error: {e}", flush=True)

def monitor_loop():
    print(f"🛡️ [MONITOR] PID {os.getpid()} - Auto-Heal active.", flush=True)
    
    # Wait for other containers to warm up
    time.sleep(10)
    
    # Bootstrap
    print("🚀 [MONITOR] Initializing Broadcast Stack...", flush=True)
    
    print("👉 Starting Worker...", flush=True)
    run_background(f"{sys.executable} -m streaming_engine.worker")
    
    print("👉 Starting Broadcast Controller (MCR)...", flush=True)
    run_background(f"{sys.executable} broadcast_controller.py")
    
    print("👉 Starting Breaking News Monitor...", flush=True)
    run_background(f"{sys.executable} breaking_news_monitor.py")
    
    print("✅ Bootstrap Complete. entering Supervisor loop.", flush=True)
    
    while True:
        try:
            # 1. Check Worker
            if not is_alive("streaming_engine.worker"):
                print("⚠️ [HEAL] Worker is DOWN!", flush=True)
                run_background(f"{sys.executable} -m streaming_engine.worker")

            # 2. Check Broadcast Controller
            if not is_alive("broadcast_controller.py"):
                print("⚠️ [HEAL] Controller (MCR) is DOWN!", flush=True)
                run_background(f"{sys.executable} broadcast_controller.py")

            # 3. Check Breaking News Monitor
            if not is_alive("breaking_news_monitor.py"):
                print("⚠️ [HEAL] Breaking News Monitor is DOWN!", flush=True)
                run_background(f"{sys.executable} breaking_news_monitor.py")

            # 3. Storage Maintenance
            cleanup_storage()

        except Exception as e:
            print(f"⚠️ [MONITOR] Loop error: {e}", flush=True)
        
        time.sleep(30)

if __name__ == '__main__':
    monitor_loop()
