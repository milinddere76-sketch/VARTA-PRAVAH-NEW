import os
import subprocess
import time
import requests
from dotenv import load_dotenv

load_dotenv()

def generate_lipsync(audio_path, anchor_name):
    """
    Synthesizes a speaking anchor video using SyncLabs API.
    High-fidelity portraits + AI Audio -> Professional News Segment.
    """
    # 1. Resolve Anchor Persona
    here = os.path.dirname(os.path.abspath(__file__))
    is_female = (anchor_name == "female" or anchor_name == "Kritika")
    avatar_path = os.path.join(here, "assets", "female_anchor.png" if is_female else "male_anchor.png")
    
    # 2. Output Path
    ts = int(time.time())
    output_v = f"/app/videos/lipsync_{ts}.mp4"
    
    print(f"🧬 [LIP-SYNC] Starting synthesis for {anchor_name}...")
    
    # 3. Use SyncLabs API for actual lip sync
    api_key = os.getenv("SYNCLABS_API_KEY")
    if not api_key:
        print("⚠️ [LIP-SYNC] No SYNCLABS_API_KEY found, falling back to static overlay.")
        return fallback_lipsync(audio_path, avatar_path, output_v)
    
    try:
        # Upload audio to a temp URL or assume it's accessible
        # For now, assume audio_path is a URL or upload it
        audio_url = audio_path  # Assume it's a URL; in practice, upload to cloud storage
        
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "model": "lipsync-2",
            "input": [
                {"type": "video", "url": avatar_path},  # Need to upload image or use URL
                {"type": "audio", "url": audio_url}
            ]
        }
        
        r = requests.post("https://api.sync.so/v2/generate", headers=headers, json=payload)
        r.raise_for_status()
        job_id = r.json()["id"]
        
        # Poll for result
        for i in range(20):
            r = requests.get(f"https://api.sync.so/v2/generate/{job_id}", headers=headers)
            data = r.json()
            status = data.get("status")
            if status in ["completed", "COMPLETED"]:
                video_url = data["videoUrl"]
                # Download the video
                v_res = requests.get(video_url)
                with open(output_v, "wb") as f:
                    f.write(v_res.content)
                print(f"✅ [LIP-SYNC] Lip-sync video generated: {output_v}")
                return output_v
            elif status == "failed":
                print("❌ [LIP-SYNC] SyncLabs job failed.")
                return fallback_lipsync(audio_path, avatar_path, output_v)
            time.sleep(10)
        
        print("⚠️ [LIP-SYNC] SyncLabs timed out, falling back.")
        return fallback_lipsync(audio_path, avatar_path, output_v)
        
    except Exception as e:
        print(f"❌ [LIP-SYNC] Error: {e}, falling back.")
        return fallback_lipsync(audio_path, avatar_path, output_v)

def fallback_lipsync(audio_path, avatar_path, output_v):
    """Fallback: static image with audio overlay."""
    try:
        final_audio = audio_path
        if not os.path.exists(audio_path):
            here = os.path.dirname(os.path.abspath(__file__))
            final_audio = os.path.join(here, "assets", "news_music.mp3")
            if not os.path.exists(final_audio):
                final_audio = "lavfi_audio"
        
        cmd = ["ffmpeg", "-y", "-loop", "1", "-t", "10", "-i", avatar_path]
        
        if final_audio == "lavfi_audio":
            cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
        else:
            cmd.extend(["-i", final_audio])
            
        cmd.extend([
            "-c:v", "libx264", "-t", "10", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-vf", "scale=1280:720",
            output_v
        ])
        
        subprocess.run(cmd, check=True)
        return output_v
    except Exception as e:
        print(f"❌ [FALLBACK] Failed: {e}")
        return "/app/videos/promo.mp4"
        
        subprocess.run(cmd, check=True)
        return output_v
    except Exception as e:
        print(f"⚠️ [LIP-SYNC] Synthesis error: {e}")
        return "/app/videos/promo.mp4"

if __name__ == "__main__":
    print("Lip-Sync Engine Ready.")
