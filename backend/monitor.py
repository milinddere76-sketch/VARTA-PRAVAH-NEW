import time
import subprocess
import os
import glob
import sys

# --- CONFIGURATION ---
MAX_FILES = 20
VIDEOS_DIR = "/app/videos"

def run_background(cmd):
    """Launches a command in the background."""
    print(f"🚀 [AUTO-HEAL] Launching: {cmd}", flush=True)
    subprocess.Popen(cmd, shell=True, start_new_session=True)

def is_alive(name_pattern):
    """Checks if a process matching the pattern is running, excluding the current process."""
    # Use pgrep -f and ensure we don't match the current process ID
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
    
    # Bootstrap: Launch everything once at start
    print("🚀 [MONITOR] Initializing Broadcast Stack...", flush=True)
    
    print("👉 Starting Worker...", flush=True)
    run_background(f"{sys.executable} -m streaming_engine.worker")
    time.sleep(2)
    
    print("👉 Starting Switcher...", flush=True)
    run_background(f"{sys.executable} switcher.py")
    time.sleep(2)
    
    print("👉 Starting Streamer...", flush=True)
    run_background("bash streamer.sh")
    time.sleep(2)
    
    print("✅ Bootstrap Complete. Entering Monitor Loop.", flush=True)
    
    while True:
        try:
            # 1. Check Worker
            if not is_alive("streaming_engine.worker"):
                print("⚠️ [HEAL] Worker is DOWN!", flush=True)
                run_background(f"{sys.executable} -m streaming_engine.worker")

            # 2. Check Switcher (Playlist Manager)
            if not is_alive("switcher.py"):
                print("⚠️ [HEAL] Switcher is DOWN!", flush=True)
                run_background("python3 /app/switcher.py")

            # 3. Check FFmpeg (Ingest Engine)
            if not is_alive("streamer.sh") and not is_alive("ffmpeg.*playlist.txt"):
                print("⚠️ [HEAL] Streamer/FFmpeg is DOWN!", flush=True)
                run_background("bash /app/streamer.sh")

            # 4. Storage Health
            cleanup_storage()

        except Exception as e:
            print(f"❌ [MONITOR] Loop Critical Error: {e}", flush=True)

        # Polling interval
        time.sleep(30)

if __name__ == "__main__":
    # Ensure correct working directory
    if os.path.exists("/app"):
        os.chdir("/app")
    
    # Force line buffering for logs
    sys.stdout.reconfigure(line_buffering=True)
    monitor_loop()
