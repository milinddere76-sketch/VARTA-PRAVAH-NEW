import subprocess
import os
import sys

def create_premium_promo(output_path):
    print(f"🎬 Creating Premium Gen-Z Promo -> {output_path}")
    
    # Absolute internal paths for Docker/Hetzner environment
    here = os.path.dirname(os.path.abspath(__file__))
    stems_dir = os.path.join(here, "promo_stems")
    
    # Emergency fallback check for absolute container path
    if not os.path.exists(stems_dir):
        stems_dir = "/app/backend/promo_stems"
    if not os.path.exists(stems_dir):
        stems_dir = "/app/promo_stems"
    
    # --- DYNAMIC & CREATIVE AUDIO SYNTHESIS ---
    # Layer 1: Kick Drum (40Hz pulse)
    kick = "sine=f=40:d=60,atrim=0:60,asetrate=44100,volume=3,tremolo=f=1:d=0.9[kick_raw];[kick_raw]lowpass=f=100[kick];"
    # Layer 2: Hi-Hat (White noise pulse)
    hat = "noise=color=white:d=60,atrim=0:60,bandpass=f=12000,volume=0.5,tremolo=f=2:d=1[hat];"
    # Layer 3: Neon Synth (Resonant Sweep)
    synth = "sine=f=440:d=60,atrim=0:60,tremolo=f=0.5:d=0.5,aecho=0.8:0.8:500:0.3[synth_raw];[synth_raw]lowpass=f=800[synth];"
    
    # --- FAILSAFE IMAGE RESOLUTION ---
    def get_input(filename, fallback_filter):
        p = os.path.join(stems_dir, filename)
        if os.path.exists(p): return ["-loop", "1", "-t", "60", "-i", p]
        return ["-f", "lavfi", "-t", "60", "-i", fallback_filter]

    v0 = get_input("globe_neon.png",   "testsrc2=s=250x250:r=30,format=rgba")
    v1 = get_input("neon_logo.png",    "color=c=cyan@0.5:s=500x200:r=30,format=rgba")
    v2 = get_input("mumbai_neon.png",  "fresnel=s=1280x720:r=30")
    v3 = get_input("silhouettes.png", "color=c=black@0.8:s=1280x200:r=30,format=rgba")

    cmd = [
        "ffmpeg", "-y",
        *v0, *v1, *v2, *v3,
        
        # Audio Synth Layers (already logic-based)
        "-f", "lavfi", "-i", kick,
        "-f", "lavfi", "-i", hat,
        "-f", "lavfi", "-i", synth,
        
        "-filter_complex", (
            # 1. Audio Mix
            "[4:a][5:a][6:a]amix=inputs=3:dropout_transition=0[outa];"

            # 2. BG Layer: Mumbai Neon with RGB Split
            "[2:v]scale=1280:720,setsar=1,hue=h='30*t':s=1.5[bg_hue];"
            "[bg_hue]split=3[r][g][b];"
            "[r]lutrgb=g=0:b=0,overlay=x='2*sin(t*5)':y=0[ro];"
            "[g]lutrgb=r=0:b=0[go];"
            "[b]lutrgb=r=0:g=0,overlay=x='-2*sin(t*5)':y=0[bo];"
            "[ro][go]blend=all_mode='addition'[rg];[rg][bo]blend=all_mode='addition'[bg_final];"
            
            # 3. Silhouettes: Breathing pulse
            "[3:v]scale=1280:-1[sil];"
            "[sil]colorkey=black:0.1:0.1,format=rgba,geq=a='if(gt(sin(t*2.5),0.4),255,100)'[sil_p];"
            
            # 4. Logo/Globe Pulsing
            "[1:v]scale=500:-1[logo];[0:v]scale=250:-1,rotate='0.5*t':c=none:ow=250:oh=250[globe];"
            
            # 5. Composite everything
            "[bg_final][sil_p]overlay=0:H-h[v1];"
            "[v1][globe]overlay=W-300:50[v2];"
            "[v2][logo]overlay=(W-w)/2:(H-h)/2[v_pre];"
            
            # 6. Neon Glitch Ticker
            "drawtext=text='VARTA PRAVAH • वार्ता प्रवाह • 24/7 LIVE • AUTHENTIC NEWS':fontcolor=0x00FFFF:fontsize=70:x=W-mod(t*250\,W+2500):y=H-120:shadowcolor=0xFF00FF:shadowx=3:shadowy=3[ticker];"
            "[v_pre][ticker]overlay=0:0[v_out]"
        ),
        "-map", "[v_out]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
        "-c:a", "aac", "-b:a", "192k", "-t", "60",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Premium Promo Created with Dynamic Audio: {output_path}")
    except Exception as e:
        print(f"Error: {e}")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=60", "-vf", "drawtext=text='VARTA PRAVAH':fontcolor=cyan:fontsize=60:x=(w-tw)/2:y=(h-th)/2", "-t", "60", output_path])



if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "premium_promo.mp4"
    create_premium_promo(out)
