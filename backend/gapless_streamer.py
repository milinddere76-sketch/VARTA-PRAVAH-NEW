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
    # Standardized to 720p (1280x720) for 1.0x speed on ARM
    print(f"🎬 [GAPLESS] Ingesting: {live_symlink} -> {rtmp_url[:30]}...")
    
    cmd = [
        "ffmpeg", "-y", "-loglevel", "info",
        "-re", "-stream_loop", "-1", "-fflags", "+genpts", "-i", live_symlink,
        "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=25",
        "-f", "lavfi", "-i", "anullsrc=cl=stereo:r=44100",
        "-filter_complex", 
        "[0:v]scale=1280:720,setsar=1[v_src];"
        "[1:v][v_src]overlay=eof_action=pass[v_out];"
        "[0:a][2:a]amix=inputs=2:dropout_transition=0:normalize=0[a_out]",
        "-map", "[v_out]", "-map", "[a_out]",
        "-r", "25", "-g", "50",
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
        "-b:v", "2000k", "-minrate", "2000k", "-maxrate", "2000k", "-bufsize", "4000k",
        "-x264-params", "nal-hrd=cbr:force-cfr=1",
        "-pix_fmt", "yuv420p", "-threads", "0",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-f", "flv", rtmp_url
    ]

    try:
        while True:
            # 1. Verify target exists, if not, wait or use fallback
            if not os.path.exists(live_symlink):
                print(f"⚠️ [GAPLESS] {time.ctime()} | Missing {live_symlink}. Attempting to restore...")
                try: 
                    if os.path.exists(initial_video):
                        if os.path.islink(live_symlink): os.remove(live_symlink)
                        os.symlink(initial_video, live_symlink)
                    else:
                        print(f"❌ [GAPLESS] {time.ctime()} | ABSOLUTE SOURCE MISSING. Waiting for restoration...")
                        time.sleep(5)
                        continue
                except: pass
            
            print(f"🚀 [GAPLESS] {time.ctime()} | Ingesting via FFmpeg...")
            subprocess.run(cmd)
            print(f"🛑 [GAPLESS] {time.ctime()} | Engine exited. Recovery in 2s...")
            time.sleep(2)
    finally:
        # Cleanup lock on exit
        if os.path.exists(lock_file): os.remove(lock_file)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gapless_streamer.py <rtmp_url> <video_path>")
        sys.exit(1)
    run_gapless_stream(sys.argv[1], sys.argv[2])
