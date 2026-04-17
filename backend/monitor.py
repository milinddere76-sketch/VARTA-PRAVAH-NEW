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
    """Checks if a process matching the pattern is running."""
    # Using pgrep -f for robust pattern matching
    # We exclude the current 'monitor.py' process itself
    return subprocess.run(f"pgrep -f '{name_pattern}'", shell=True, capture_output=True).returncode == 0

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
    print("🛡️ [MONITOR] Auto-Heal & Storage Watch active.", flush=True)
    
    while True:
        try:
            # 1. Check Worker (Core)
            if not is_alive("streaming_engine.worker"):
                print("⚠️ [HEAL] Worker is DOWN!", flush=True)
                run_background("python3 -m streaming_engine.worker")

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
