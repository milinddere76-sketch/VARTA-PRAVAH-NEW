import subprocess
import os
import sys

def create_premium_promo(output_path):
    print(f"Creating Premium Studio Promo -> {output_path}")
    
    here = os.path.dirname(os.path.abspath(__file__))
    stems_dir = os.path.join(here, "promo_stems")
    
    # Environment absolute path fallback
    if not os.path.exists(stems_dir):
        stems_dir = "/app/backend/promo_stems"
    if not os.path.exists(stems_dir):
        stems_dir = "/app/promo_stems"
        
    # Dynamically find MP4 stems to use (prioritizing 'clip*', then 't*')
    clips = [f for f in os.listdir(stems_dir) if f.startswith("clip") and f.endswith(".mp4")]
    if not clips:
         clips = [f for f in os.listdir(stems_dir) if f.startswith("t") and f.endswith(".mp4")]
         
    # Generate concat file cleanly with absolute paths
    concat_txt_path = os.path.join(stems_dir, "dynamic_concat.txt")
    with open(concat_txt_path, "w", encoding="utf-8") as f:
        # Loop clips to ensure it surpasses the 60s target
        for _ in range(15): 
            for clip in sorted(clips):
                # FFmpeg requires absolute paths formatted appropriately
                clean_path = os.path.join(stems_dir, clip).replace('\\', '/')
                f.write(f"file '{clean_path}'\n")
                
    music_path = os.path.join(stems_dir, "news_music.mp3")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_txt_path
    ]
    
    if os.path.exists(music_path):
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
        audio_map = "1:a"
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=cl=stereo:r=44100"])
        audio_map = "1:a"

    overlay_filter = (
        "[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720[vbg];"
        "drawtext=text='VARTA PRAVAH | 24/7 LIVE | AUTHENTIC MAHARASHTRA NEWS | NEXT BULLETIN COMING SOON...':"
        "fontcolor=white:fontsize=50:box=1:boxcolor=red@0.9:boxborderw=10:"
        "x=W-mod(t*200\\,W+4000):y=H-90[v_out]"
    )

    cmd.extend([
        "-filter_complex", overlay_filter,
        "-map", "[v_out]",
        "-map", audio_map,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac", "-b:a", "192k", 
        "-t", "60",
        "-r", "25",
        output_path
    ])
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Premium Studio Promo Created using True Stems: {output_path}")
    except Exception as e:
        print(f"Error Generating Promo: {e}")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "premium_promo.mp4"
    create_premium_promo(out)
