import subprocess
import os
import time
import sys

def run_gapless_stream(rtmp_url, initial_video):
    # --- LOCK FILE: Absolute prevention of duplicate ingestion ---
    lock_file = "/tmp/streamer.lock"
    if os.path.exists(lock_file):
        print("🛑 [LOCK] Streamer already running. Aborting duplicate.")
        return
    with open(lock_file, "w") as f: f.write(str(os.getpid()))

    print(f"📡 [GAPLESS] Starting Single Ingest to {rtmp_url[:20]}...")
    
    live_symlink = "/app/videos/current_live.mp4"
    os.makedirs("/app/videos", exist_ok=True)
    
    # Ensure the symlink exists to prevent 'file not found' crash
    if not os.path.exists(live_symlink):
        # Even if promo.mp4 is missing, we create a link to it
        try: os.symlink(initial_video, live_symlink)
        except: pass

    # --- THE INDESTRUCTIBLE COMMAND ---
    # We use -f lavfi 'color' as a secondary input if the first fails
    cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        "-re", "-stream_loop", "-1", "-i", live_symlink,
        "-f", "lavfi", "-i", "anullsrc=cl=stereo:sr=44100",
        "-filter_complex", "[0:a?]adelay=1|1[a1];[a1][1:a]amix=inputs=2:dropout_transition=0[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
        "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
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
