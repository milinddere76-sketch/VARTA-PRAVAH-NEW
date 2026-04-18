#!/usr/bin/env python3
"""
Gen-Z Neon Promo Video Generator — VartaPravah (Pillow-Overlay Edition)
=======================================================================
This version uses Pillow (PIL) to render text as transparent PNG layers.
This bypasses FFmpeg's Fontconfig issues on Windows and ensures high-quality
Marathi rendering across all platforms.
"""

import subprocess
import os
import sys
import platform
from PIL import Image, ImageDraw, ImageFont


def create_genz_promo(output_path: str = None) -> bool:
    # ── Resolve paths ──────────────────────────────────────────────
    if output_path is None:
        if os.path.isdir("/app"):
            output_path = "/app/videos/promo.mp4"
        else:
            here = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(here, "videos", "promo.mp4")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    temp_dir = os.path.dirname(output_path)
    
    print(f"Gen-Z Promo Generator (Pillow Edition) - output: {output_path}")

    # ── Font Selection ──────────────────────────────────────────────
    if platform.system() == "Windows":
        # Nirmala is the standard Devanagari font on Win 10/11
        font_marathi = "C:/Windows/Fonts/Nirmala.ttf"
        font_english = "C:/Windows/Fonts/Arial.ttf"
        font_bold    = "C:/Windows/Fonts/Arialbd.ttf"
    else:
        # Linux paths (for Docker)
        font_marathi = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
        font_english = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        font_bold    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # Fallback to defaults if specific paths aren't found
    if not os.path.exists(font_marathi): font_marathi = "arial"
    if not os.path.exists(font_english): font_english = "arial"
    if not os.path.exists(font_bold):    font_bold    = "arial"

    # ── Render Text Layers using Pillow ───────────────────────────
    print("Rendering text layers via Pillow...")
    
    # Layer 1: Title + Subtitle
    layer_main = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer_main)
    
    try:
        # Title Glow (Magenta)
        f_title = ImageFont.truetype(font_marathi, 100)
        title_text = "वार्ता प्रवाह"
        # Draw soft glow (offset)
        draw.text((640-5, 230-5), title_text, font=f_title, fill=(255, 0, 170, 180), anchor="mm")
        draw.text((640+5, 230+5), title_text, font=f_title, fill=(0, 255, 238, 180), anchor="mm")
        # Main white text
        draw.text((640, 230), title_text, font=f_title, fill=(255, 255, 255, 255), anchor="mm")
        
        # English Subtitle
        f_sub = ImageFont.truetype(font_bold, 50)
        draw.text((640, 340), "VARTA PRAVAH", font=f_sub, fill=(0, 255, 238, 255), anchor="mm")
        
        # Tagline
        f_tag = ImageFont.truetype(font_english, 24)
        draw.text((640, 400), "24x7 AI-Powered Marathi News", font=f_tag, fill=(180, 180, 180, 255), anchor="mm")
        
        # LIVE Badge (Permanent part)
        f_live = ImageFont.truetype(font_bold, 24)
        draw.text((60, 40), "LIVE", font=f_live, fill=(255, 50, 50, 255), anchor="mm")
        draw.ellipse([35, 33, 45, 43], fill=(255, 50, 50, 255))
        
    except Exception as e:
        print(f"Pillow render warning: {e}")
        # Draw basic text if Marathi font fails
        draw.text((640, 230), "Varta Pravah", fill="white", anchor="mm")

    main_png = os.path.join(temp_dir, "promo_layer_main.png")
    layer_main.save(main_png)

    # Layer 2: Scrolling Ticker (Long image)
    ticker_text = "BREAKING NEWS  |  Maharashtra  |  India  |  World News  |  Varta Pravah 24x7  |  AI-Powered Marathi Broadcasting  |  "
    f_ticker = ImageFont.truetype(font_bold, 28)
    # Estimate width
    ticker_w = f_ticker.getlength(ticker_text)
    layer_ticker = Image.new("RGBA", (int(ticker_w) + 100, 80), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(layer_ticker)
    tdraw.text((0, 40), ticker_text, font=f_ticker, fill=(255, 255, 255, 255), anchor="lm")
    
    ticker_png = os.path.join(temp_dir, "promo_layer_ticker.png")
    layer_ticker.save(ticker_png)

    # ── FFmpeg Composition ──────────────────────────────────────────
    print("Composing video via FFmpeg...")
    
    # Path helpers for FFmpeg
    def ff_p(p): return p.replace("\\", "/")

    # Filter description:
    # 1. Start with dark blue background
    # 2. Add hue shift for neon feel
    # 3. Add scanlines
    # 4. Overlay main text static layer
    # 5. Overlay ticker moving layer
    filter_complex = (
        # Background base pulse
        # High-energy vibrant neon background (static for cross-platform stability)
        "[bg]hue=h=280:s=1.2[pulsed];"
        "[pulsed]drawgrid=w=0:h=8:c=black@0.12:t=1[grid];"
        # Accent boxes
        "[grid]drawbox=x=0:y=0:w=iw:h=6:c=0xff00bb@1:t=fill[top];"
        "[top]drawbox=x=0:y=ih-90:w=iw:h=90:c=0x000000cc:t=fill[ticker_bg];"
        "[ticker_bg]drawbox=x=0:y=ih-93:w=iw:h=3:c=0xff00bb@1:t=fill[div];"
        # Overlays
        "[div][1:v]overlay=0:0[with_main];"
        f"[with_main][2:v]overlay=x='w-mod(200*t,w+{int(ticker_w)})':y=H-65[outv]"
    )

    cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        # ── DRAMATIC NEWS BEAT SYNTHESIS ──
        # Kick pulse every 1s + Metallic ping loop
        "-f", "lavfi", "-i", (
            "sine=f=55:d=60,tremolo=f=1:d=1,lowpass=f=80[kick];"
            "sine=f=660:d=60,tremolo=f=2:d=0.5,aecho=0.8:0.8:400:0.5[ping];"
            "[kick][ping]amix=inputs=2:weights=1 0.4,volume=1.8[outa]"
        ),
        "-i", ff_p(main_png),
        "-i", ff_p(ticker_png),
        "-t", "60",
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-b:v", "1000k", "-c:a", "aac", "-b:a", "128k",
        ff_p(output_path)
    ]

    result = subprocess.run(cmd, text=True, timeout=600)

    # Cleanup temp layers
    try:
        os.remove(main_png)
        os.remove(ticker_png)
    except:
        pass

    if result.returncode == 0 and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1_048_576
        print(f"Gen-Z promo ready: {output_path}  ({size_mb:.1f} MB)")
        # Clear sentinel
        sentinel_path = os.path.join(os.path.dirname(output_path), ".promo_studio_ok")
        try:
            open(sentinel_path, "w").close()
        except:
            pass
        return True
    else:
        print(f"FFmpeg composition failed (exit {result.returncode})")
        return False


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else None
    ok  = create_genz_promo(out)
    sys.exit(0 if ok else 1)
