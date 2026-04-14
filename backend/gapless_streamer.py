import subprocess
import os
import time
import sys

def run_gapless_stream(rtmp_url, initial_video):
    print(f"📡 [GAPLESS] Starting Permanent Ingest to {rtmp_url[:20]}...")
    
    live_symlink = "/app/videos/current_live.mp4"
    os.makedirs("/app/videos", exist_ok=True)
    
    # Ensure the symlink exists on first run
    if not os.path.exists(live_symlink):
        os.symlink(initial_video, live_symlink)

    # Indestructible loop on the symlink
    cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        "-re", "-stream_loop", "-1", "-i", live_symlink,
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
        "-b:v", "2800k", "-maxrate", "3000k", "-bufsize", "6000k",
        "-pix_fmt", "yuv420p", "-g", "60",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-f", "flv", rtmp_url
    ]

    while True:
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"⚠️ [GAPLESS] Ingest hiccup: {e}. Recovering...")
            time.sleep(2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gapless_streamer.py <rtmp_url> <video_path>")
        sys.exit(1)
    run_gapless_stream(sys.argv[1], sys.argv[2])
