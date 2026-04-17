import time
import subprocess
import os
import glob

# --- CONFIGURATION ---
MAX_FILES = 20
VIDEOS_DIR = "/app/videos"

def run_background(cmd):
    """Launches a command in the background."""
    print(f"🚀 [AUTO-HEAL] Launching: {cmd}")
    subprocess.Popen(cmd, shell=True, start_new_session=True)

def is_alive(name_pattern):
    """Checks if a process matching the pattern is running."""
    # Using pgrep -f for robust pattern matching
    return subprocess.run(f"pgrep -f '{name_pattern}'", shell=True, capture_output=True).returncode == 0

def cleanup_storage():
    """Keeps disk usage in check."""
    try:
        files = sorted(glob.glob(os.path.join(VIDEOS_DIR, "news_*.mp4")), key=os.path.getctime)
        if len(files) > MAX_FILES:
            to_delete = files[:-MAX_FILES]
            print(f"🧹 [MONITOR] Cleaning up {len(to_delete)} old videos.")
            for f in to_delete:
                try: os.remove(f)
                except: pass
    except Exception as e:
        print(f"⚠️ [MONITOR] Cleanup error: {e}")

def monitor_loop():
    print("🛡️ [MONITOR] Auto-Heal & Storage Watch active.")
    
    while True:
        try:
            # 1. Check Worker (Core)
            if not is_alive("streaming_engine.worker"):
                print("⚠️ [HEAL] Worker is DOWN!")
                run_background("python3 -m streaming_engine.worker")

            # 2. Check Switcher (Playlist Manager)
            if not is_alive("switcher.py"):
                print("⚠️ [HEAL] Switcher is DOWN!")
                run_background("python3 /app/switcher.py")

            # 3. Check FFmpeg (Ingest Engine)
            # We check for both the shell script and the ffmpeg process it spawns
            if not is_alive("streamer.sh") and not is_alive("ffmpeg.*playlist.txt"):
                print("⚠️ [HEAL] Streamer/FFmpeg is DOWN!")
                run_background("bash /app/streamer.sh")

            # 4. Storage Health
            cleanup_storage()

        except Exception as e:
            print(f"❌ [MONITOR] Loop Critical Error: {e}")

        # Polling interval (30 seconds as requested)
        time.sleep(30)

if __name__ == "__main__":
    # Ensure correct working directory inside container
    if os.path.exists("/app"):
        os.chdir("/app")
    monitor_loop()
