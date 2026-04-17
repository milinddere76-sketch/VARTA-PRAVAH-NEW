import os
import time
import subprocess
from lip_sync import generate_lipsync

def create_video(data):
    """
    Renders the final news bulletin video by combining 
    lip-synced anchor footage with a news ticker.
    """
    audio_path, ticker, anchor = data

    # 1. Unique Output Path for 24/7 Stability
    ts = int(time.time())
    output = f"/app/videos/news_{ts}.mp4"

    print(f"🎬 [RENDERER] Starting Final Composite for {anchor}...")

    try:
        # 2. Step 1: Generate Lip-Synced Footage
        # This uses the high-fidelity portraits and the generated audio
        lipsync_v = generate_lipsync(audio_path, anchor)

        # 3. Step 2: FFmpeg Composite (Draw Ticker Overlay)
        # We use a black semi-transparent box for ticker readability
        cmd = [
            "ffmpeg", "-y", "-i", lipsync_v,
            "-vf", f"drawtext=text='{ticker}':x=10:y=h-45:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.6",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "128k", 
            output
        ]
        
        subprocess.run(cmd, check=True)
        print(f"✅ [RENDERER] Broadcast segment ready: {output}")
        
        # Cleanup temporary lipsync file to save space (optional but recommended)
        if "lipsync_" in lipsync_v and os.path.exists(lipsync_v):
            os.remove(lipsync_v)
            
        return output
        
    except Exception as e:
        print(f"❌ [RENDERER] Critical failure: {e}")
        # Return promo as emergency fallback to keep stream alive
        return "/app/videos/promo.mp4"
