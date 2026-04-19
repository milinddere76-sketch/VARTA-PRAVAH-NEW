import subprocess
import os
import sys
import platform
import random
from PIL import Image, ImageDraw, ImageFont

def _get_latest_news_headlines() -> str:
    """Safely retrieves the latest 5 headlines from the DB to make the ticker dynamic."""
    try:
        from database import SessionLocal
        from models import News
        db = SessionLocal()
        # Fetch latest 5 Marathi news
        articles = db.query(News).filter(News.language == "Marathi").order_by(News.created_at.desc()).limit(5).all()
        db.close()
        
        if articles:
            texts = [a.headline.strip() for a in articles]
            return "  |  ".join(texts)
    except Exception as e:
        print(f"Ticker dynamic fetch failed: {e}")
    
    # Static fallback
    return "VARTA PRAVAH NEWS LIVE  |  AUTHENTIC MAHARASHTRA NEWS  |  AI-POWERED BROADCASTING  |  FOLLOW FOR MORE UPDATES"

def create_premium_promo(output_path: str = None) -> bool:
    # ── Resolve paths ──────────────────────────────────────────────
    here = os.path.dirname(os.path.abspath(__file__))
    if output_path is None:
        output_path = os.path.join(here, "videos", "promo.mp4")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_dir = os.path.dirname(output_path)
    
    # Try multiple potential locations for stems
    possible_stems = [
        os.path.join(here, "promo_stems"),
        "/app/backend/promo_stems",
        "/app/promo_stems",
        "./promo_stems"
    ]
    
    stems_dir = None
    for p in possible_stems:
        if os.path.exists(p) and os.listdir(p):
            stems_dir = p
            break
            
    if not stems_dir:
        print("⚠️ No promo_stems directory found. Creating recovery placeholder...")
        stems_dir = os.path.join(temp_dir, "recovery_stems")
        os.makedirs(stems_dir, exist_ok=True)
        # Create a blank neon logo if master is missing
        if not os.path.exists(os.path.join(here, "assets", "varta_logo.png")):
            logo = Image.new("RGBA", (200, 200), (0, 255, 255, 100))
            logo.save(os.path.join(stems_dir, "neon_logo.png"))
        
    print(f"🚀 Using stems from -> {stems_dir}")

    # ── Font Selection (Robust Discovery) ──────────────────────────
    def find_font(candidates):
        for c in candidates:
            if os.path.exists(c): return c
        return "arial" # Final OS fallback

    if platform.system() == "Windows":
        font_marathi = find_font(["C:/Windows/Fonts/Nirmala.ttf", "C:/Windows/Fonts/mangal.ttf"])
        font_english = find_font(["C:/Windows/Fonts/Arial.ttf"])
        font_bold    = find_font(["C:/Windows/Fonts/Arialbd.ttf"])
    else:
        # Linux / Docker paths
        font_marathi = find_font([
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoDevanagari-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ])
        font_english = find_font(["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"])
        font_bold    = find_font(["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"])

    # ── Render UI Layers via Pillow ────────────────────────────────
    print("🎨 Rendering high-fidelity UI layers...")
    
    # Layer 1: Static Branding (Logo, Corner Accents)
    layer_ui = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer_ui)
    
    try:
        # Title with Glow
        f_title = ImageFont.truetype(font_marathi, 80)
        title_text = "वार्ता प्रवाह"
        # Glow
        draw.text((640-3, 220-3), title_text, font=f_title, fill=(0, 255, 255, 120), anchor="mm")
        draw.text((640+3, 220+3), title_text, font=f_title, fill=(255, 0, 255, 120), anchor="mm")
        draw.text((640, 220), title_text, font=f_title, fill=(255, 255, 255, 255), anchor="mm")
        
        # Sub-branding
        f_sub = ImageFont.truetype(font_bold, 40)
        draw.text((640, 310), "VARTA PRAVAH NEWS", font=f_sub, fill=(255, 255, 255, 230), anchor="mm")
        
        # Slogan
        f_slogan = ImageFont.truetype(font_marathi, 30)
        draw.text((640, 370), "विश्वासार्हता आणि वेग", font=f_slogan, fill=(0, 255, 238, 255), anchor="mm")

        # Top Left: LIVE indicator
        draw.rectangle([40, 40, 140, 80], fill=(255, 0, 0, 200), outline="white", width=2)
        f_live = ImageFont.truetype(font_bold, 24)
        draw.text((90, 60), "LIVE", font=f_live, fill="white", anchor="mm")

    except Exception as e:
        print(f"Pillow Layer 1 Error: {e}")

    ui_png = os.path.join(temp_dir, "premium_layer_ui.png")
    layer_ui.save(ui_png)

    # Layer 2: Long Scrolling Ticker (Dynamic News)
    headlines = _get_latest_news_headlines()
    ticker_text = f"  🔥🔥 BREAKING NEWS: {headlines}  |  VARTA PRAVAH: NEXT BULLETIN STARTING SOON  🔥🔥  "
    f_ticker = ImageFont.truetype(font_marathi, 32) # Use Marathi font for headlines
    t_width = int(f_ticker.getlength(ticker_text))
    layer_ticker = Image.new("RGBA", (t_width + 100, 100), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(layer_ticker)
    tdraw.text((0, 50), ticker_text, font=f_ticker, fill=(255, 255, 255, 255), anchor="lm")
    
    ticker_png = os.path.join(temp_dir, "premium_layer_ticker.png")
    layer_ticker.save(ticker_png)

    # ── Background Concat Logic ────────────────────────────────────
    print("🎬 Preparing dynamic background loop...")
    clips = [f for f in os.listdir(stems_dir) if (f.startswith("clip") or f.startswith("t")) and f.endswith(".mp4")]
    
    concat_txt_path = os.path.join(temp_dir, "premium_concat.txt")
    if not clips:
        print("📺 No clips found - Activating Studio Emergency Mode (Synthetic Background)")
        # Create an empty file to satisfy the logic if needed, but we'll swap inputs
    else:
        random.shuffle(clips) # High energy variety
        with open(concat_txt_path, "w", encoding="utf-8") as f:
            # Loop to ensure we hit 60s
            for _ in range(20):
                for clip in clips:
                    clean_path = os.path.join(stems_dir, clip).replace('\\', '/')
                    f.write(f"file '{clean_path}'\n")

    # ── FFmpeg Composition ──────────────────────────────────────────
    print("📽️ Composing core broadcast file...")
    def ff_p(p): return p.replace("\\", "/")
    
    # Priority Logo
    master_logo = os.path.join(here, "assets", "varta_logo.png")
    if os.path.exists(master_logo):
        logo_path = master_logo
        print(f"💎 Using Master Logo -> {logo_path}")
    else:
        logo_path = os.path.join(stems_dir, "neon_logo.png")
        print(f"🛡️ Using Fallback Logo -> {logo_path}")
    
    music_path = os.path.join(stems_dir, "news_music.mp3")

    filter_complex = (
        "[0:v]scale=1280:720,setsar=1[vbg];"
        # Animated logo: breathing effect (scales in/out every 5 seconds)
        "[3:v]scale='150*(1+0.2*sin(2*PI*t/5))':-1,format=rgba,colorchannelmixer=aa=0.85[pulse_logo];"
        "[vbg][pulse_logo]overlay=W-w-50:50[v1];"
        # Add UI Layer with fade-in effect
        "[1:v]format=rgba,fade=t=in:st=0:d=2:alpha=1[faded_ui];"
        "[v1][faded_ui]overlay=0:0[v2];"
        # Ticker Box (Red glassmorphism feel)
        "[v2]drawbox=y=ih-100:w=iw:h=100:color=red@0.8:t=fill[v3];"
        "[v3]drawbox=y=ih-103:w=iw:h=3:color=white@0.9:t=fill[v4];"
        # Scrolling Ticker Overlay with variable speed
        f"[v4][2:v]overlay=x='w-mod((200+50*sin(2*PI*t/10))*t,w+{t_width})':y=H-85[outv]"
    )

    # Re-map inputs based on Emergency Mode
    if not clips:
        # Emergency mode uses filter for input 0
        inputs = [
            "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=60",
            "-i", ff_p(ui_png),
            "-i", ff_p(ticker_png),
            "-i", ff_p(logo_path)
        ]
        # v1: black + ui, v2: v1 + ticker, v3: v2 + logo (scaled)
        filter_complex = (
            "[0:v][1:v]overlay=0:0[v1];"
            f"[v1][2:v]overlay=x='w-mod((200+50*sin(2*PI*t/10))*t,w+{t_width})':y=H-75[v2];"
            "[3:v]scale='180*(1+0.1*sin(2*PI*t/6))':-1[logo_animated];"
            "[v2][logo_animated]overlay=1080:20[outv]"
        )
    else:
        inputs = [
            "-f", "concat", "-safe", "0", "-i", ff_p(concat_txt_path),
            "-i", ff_p(ui_png),
            "-i", ff_p(ticker_png),
            "-i", ff_p(logo_path)
        ]
    
    audio_map = ""
    # Check for music in stems or assets
    assets_music = os.path.join(here, "assets", "news_music.mp3")
    if os.path.exists(assets_music) and os.path.getsize(assets_music) > 0:
        music_path = assets_music
        
    if os.path.exists(music_path) and os.path.getsize(music_path) > 0:
        inputs.extend(["-stream_loop", "-1", "-i", ff_p(music_path)])
        # Current input 0-3 are video, 4 is music
        audio_map = "[4:a]volume=1.0[outa]"
    else:
        # Generate professional "News Theme" audio (mix of tones for urgency and professionalism)
        # Low hum + mid tension + high alert beeps
        news_audio = (
            "sine=f=80:d=60,volume=0.3[hum];"  # Deep bass hum
            "sine=f=400:d=60,volume=0.2[tension];"  # Mid tension
            "sine=f=1000:d=60,volume=0.1[alert];"  # High alert
            "[hum][tension]amix=inputs=2:duration=first[base];"
            "[base][alert]amix=inputs=2:duration=first[out_news]"
        )
        inputs.extend(["-f", "lavfi", "-i", news_audio])
        # Current input 0-3 are video, 4 is lavfi
        audio_map = "[4:a]volume=1.0[outa]"

    cmd = [
        "ffmpeg", "-y", "-loglevel", "warning"
    ] + inputs + [
        "-filter_complex", filter_complex + ";" + audio_map,
        "-map", "[outv]", "-map", "[outa]",
        "-t", "60",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        ff_p(output_path)
    ]

    try:
        subprocess.run(cmd, check=True, timeout=300)
        print(f"✨ PREMIUM PROMO READY: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error Generating Premium Promo: {e}")
        return False
    finally:
        # Cleanup
        for p in [ui_png, ticker_png, concat_txt_path]:
            try: os.remove(p)
            except: pass

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else None
    create_premium_promo(out)

