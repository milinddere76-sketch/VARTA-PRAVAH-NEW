import subprocess
import os
import sys

def create_premium_promo(output_path):
    print(f"🎬 Creating Premium Gen-Z Promo -> {output_path}")
    
    # Paths to stems (now inside backend/ on server)
    stems_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "promo_stems")
    has_assets = os.path.exists(os.path.join(stems_dir, "globe_neon.png")) and os.path.exists(os.path.join(stems_dir, "neon_logo.png"))
    
    if not has_assets:
        print("⚠️  Missing premium stems. Using procedural fallback.")
        # FALLBACK: Create a cool dynamic grid with text if assets are missing
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=f=40:d=60",
            "-vf", "hue=h=240:s=0.5,drawtext=text='VARTA PRAVAH':fontcolor=white:fontsize=80:x=(w-tw)/2:y=(h-th)/2:box=1:boxcolor=black@0.5:boxborderw=20",
            "-t", "60", "-pix_fmt", "yuv420p", output_path
        ]
        subprocess.run(cmd, check=True)
        return
    
    # We'll use a complex filter graph to create animations
    # 1. Background: Concatenate clips with glitch transitions
    # 2. Overlay 1: Neon Globe (pulsing)
    # 3. Overlay 2: News Ticker
    # 4. Audio: Low-fi "cyber" beat generated via lavfi
    
    # 3. Check for Manual Creative Music Override
    manual_music = os.path.join(os.path.dirname(os.path.abspath(__file__)), "creative_music.mp3")
    if os.path.exists(manual_music):
        audio_input = ["-i", manual_music]
        audio_map = ["-map", "3:a", "-c:a", "aac", "-b:a", "192k"]
        print("🎵 Using manual creative_music.mp3 found in backend.")
    else:
        # High-Quality procedural Lo-Fi Synth Beat
        audio_input = [
            "-f", "lavfi", "-i", 
            "sine=f=55:d=60,tremolo=f=1:d=1,lowpass=f=100[kick];"
            "sine=f=440:d=60,tremolo=f=0.5:d=0.8,aecho=0.8:0.8:1000:0.5,highpass=f=200[pad];"
            "sine=f=880:d=60,tremolo=f=4:d=0.2,aecho=0.8:0.9:500:0.3[lead];"
            "[kick][pad][lead]amix=inputs=3:weights=1 0.4 0.2,volume=2.5[outa]"
        ]
        audio_map = ["-map", "[outa]", "-c:a", "aac", "-b:a", "128k"]
        print("🎹 Generating procedural Creative Lo-Fi Beat.")

    cmd = [
        "ffmpeg", "-y",
        # Inputs
        "-loop", "1", "-t", "60", "-i", os.path.join(stems_dir, "globe_neon.png"),  # [0:v]
        "-loop", "1", "-t", "60", "-i", os.path.join(stems_dir, "neon_logo.png"),   # [1:v]
        "-stream_loop", "-1", "-t", "60", "-i", os.path.join(stems_dir, "raw_concat.mp4"), # [2:v] (8s loop)
    ] + audio_input + [
        "-filter_complex", (
            # 1. Base Loop (Looped to 60s)
            "[2:v]scale=1280:720,setsar=1[base];"
            
            # 2. Globe Overlay (Bottom Right, pulsing)
            "[0:v]scale=350:-1[globe_s];"
            "[globe_s]format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*(0.8+0.2*sin(2*PI*t/3))'[globe_pulsed];"
            
            # 3. Pulsing Logo (Center, Brightness pulse)
            "[1:v]scale=600:-1[logo_s];"
            "[logo_s]geq=r='r(X,Y)*(1+0.2*sin(2*PI*t/2))':g='g(X,Y)*(1+0.2*sin(2*PI*t/2))':b='b(X,Y)*(1+0.2*sin(2*PI*t/2))'[logo_p];"
            
            # 4. Compose
            "[base][globe_pulsed]overlay=W-400:H-400[tmp1];"
            "[tmp1][logo_p]overlay=(W-w)/2:(H-h)/2-50[v_pre];"
            
            # 5. Vignette and Color Grading
            "[v_pre]vignette=angle=0.5,hue=s=1.2[v_final]"
        ),
        "-map", "[v_final]",
    ] + audio_map + [
        "-c:v", "libx264", "-preset", "ultrafast",
        "-b:v", "2500k", "-minrate", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
        "-pix_fmt", "yuv420p", "-g", "60",
        "-t", "60",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Premium Promo Created: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create premium promo: {e.stderr.decode()}")
        # Fallback: copy raw_concat if main fails
        subprocess.run(["ffmpeg", "-y", "-i", os.path.join(stems_dir, "raw_concat.mp4"), "-t", "60", output_path])

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "premium_promo.mp4"
    create_premium_promo(out)
