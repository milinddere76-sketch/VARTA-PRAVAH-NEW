import subprocess
import os
import time
import sys

def run_gapless_stream(rtmp_url, initial_video):
    # --- SMART LOCK: Check if the process is REALLY alive ---
    lock_file = "/tmp/streamer.pid"
    if os.path.exists(lock_file):
        with open(lock_file, "r") as f:
            old_pid = f.read().strip()
            if old_pid and os.path.exists(f"/proc/{old_pid}"):
                print(f"🛑 [LOCK] Streamer already running (PID {old_pid}). Aborting.")
                return
        os.remove(lock_file)
    
    with open(lock_file, "w") as f: f.write(str(os.getpid()))

    print(f"📡 [GAPLESS] Starting Single Ingest to {rtmp_url[:20]}...")
    
    # Absolute paths are required for stable Docker symlinks
    base_dir = "/app"
    live_symlink = os.path.join(base_dir, "videos", "current_live.mp4")
    os.makedirs(os.path.join(base_dir, "videos"), exist_ok=True)
    
    if not os.path.isabs(initial_video):
        initial_video = os.path.join(base_dir, initial_video)

    # --- THE INDESTRUCTIBLE COMMAND ---
    # We use -f lavfi 'color' as a secondary input if the first fails
    cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        "-re", "-stream_loop", "-1", "-i", live_symlink,
        "-f", "lavfi", "-i", "anullsrc=cl=stereo:sr=44100",
        "-filter_complex", "[0:a]amix=inputs=2:dropout_transition=0:normalize=0[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
        "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k",
        "-pix_fmt", "yuv420p", "-g", "60",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-f", "flv", rtmp_url
    ]

    try:
        while True:
            # If the symlink is broken, FFmpeg might exit. We catch and retry.
            if not os.path.exists(live_symlink):
                print("⚠️ [GAPLESS] Source missing. Fixing symlink...")
                try: os.symlink(initial_video, live_symlink)
                except: pass
            
            subprocess.run(cmd)
            time.sleep(1)
    finally:
        # Cleanup lock on exit
        if os.path.exists(lock_file): os.remove(lock_file)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gapless_streamer.py <rtmp_url> <video_path>")
        sys.exit(1)
    run_gapless_stream(sys.argv[1], sys.argv[2])
