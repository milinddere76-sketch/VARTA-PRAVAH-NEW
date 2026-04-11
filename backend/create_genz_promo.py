#!/usr/bin/env python3
"""
Gen-Z Neon Promo Video Generator — VartaPravah
===============================================
Creates a 60-second animated neon promo and saves it as promo.mp4.

Run manually inside Docker:
  docker exec $(docker ps -qf name=backend) python create_genz_promo.py

Or locally (requires FFmpeg on PATH):
  python create_genz_promo.py [output_path]
"""

import subprocess
import os
import sys


def create_genz_promo(output_path: str = None) -> bool:
    # ── Resolve output path ────────────────────────────────────────
    if output_path is None:
        if os.path.isdir("/app"):
            output_path = "/app/videos/promo.mp4"
        else:
            here = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(here, "videos", "promo.mp4")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sentinel_path = os.path.join(os.path.dirname(output_path), ".promo_studio_ok")

    # Ensure UTF-8 output for Windows consoles
    import platform
    import tempfile
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(f"Gen-Z Promo Generator - output: {output_path}")
    print("Generating 60s animated neon promo...")

    # ── Font paths (OS-aware) ──────────────────────────────────
    WIN_MODE = platform.system() == "Windows"
    if WIN_MODE:
        NOTO = "Nirmala UI"; DEJA_B = "Arial Bold"; DEJA = "Arial"
    else:
        NOTO = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
        DEJA_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        DEJA = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    PI     = "3.14159265"

    # ── Temp text files (avoids shell-escaping Marathi inline) ────
    tmp_dir = tempfile.gettempdir()
    title_file  = os.path.join(tmp_dir, "vp_genz_title.txt")
    ticker_file = os.path.join(tmp_dir, "vp_genz_ticker.txt")
    try:
        with open(title_file, "w", encoding="utf-8") as f:
            f.write("वार्ता प्रवाह")
        with open(ticker_file, "w", encoding="utf-8") as f:
            f.write(
                "BREAKING NEWS  |  Maharashtra  |  India  |  World News  |  "
                "Varta Pravah 24x7  |  AI-Powered Marathi Broadcasting  |  "
            )
    except Exception as e:
        print(f"⚠️  Could not write temp text files: {e}")
        title_file  = None
        ticker_file = None

    # ── Build video filter chain ───────────────────────────────────
    # Lightweight alternative to geq for animated neon aesthetic:
    # A dark blue background with additive grain and neon border effects.
    vf_parts = [
        # 1. Base dark blue color (Gen-Z vibe)
        "color=c=0x0d1120:size=1280x720:rate=30",
        
        # 2. Add subtle animated neon pulse via hue filter
        "hue='h=360*sin(2*PI*t/12):s=1+0.2*sin(2*PI*t/5)'",

        # 3. Cyberpunk texture
        "drawgrid=width=0:height=8:color=black@0.12:thickness=1",

        # 3. Left & right vertical neon accent bars
        "drawbox=x=0:y=6:w=6:h=ih-100:color=0xff00bb@0.85:t=fill",
        "drawbox=x=iw-6:y=6:w=6:h=ih-100:color=0x00ffcc@0.85:t=fill",

        # 4. Top magenta accent strip
        "drawbox=x=0:y=0:w=iw:h=6:color=0xff00bb@1:t=fill",

        # 5. Ticker zone background
        "drawbox=x=0:y=ih-90:w=iw:h=90:color=0x000000cc:t=fill",

        # 6. Magenta separator above ticker
        "drawbox=x=0:y=ih-93:w=iw:h=3:color=0xff00bb@1:t=fill",

        # 7. Bottom cyan strip
        "drawbox=x=0:y=ih-4:w=iw:h=4:color=0x00ffcc@1:t=fill",
    ]

    # Helper to escape Windows paths for FFmpeg filters
    def ff_path(p):
        if platform.system() == "Windows":
            p = p.replace("\\", "/")
            return p.replace(":", "\\:")
        return p

    # 8-10. Marathi title with layered neon glow
    title_src = f"textfile='{ff_path(title_file)}'" if title_file else "text='Varta Pravah'"
    f_noto = ff_path(NOTO)
    f_deja_b = ff_path(DEJA_B)
    f_deja = ff_path(DEJA)

    # On Windows, use 'font=' name instead of 'fontfile=' path
    font_key = "font" if WIN_MODE else "fontfile"

    vf_parts += [
        # Cyan glow layer
        (
            f"drawtext={title_src}:{font_key}='{f_noto}':"
            f"fontsize=120:fontcolor=0x00ffee@0.5:"
            f"x=(w-text_w)/2+7:y=(h-text_h)/2-118+7"
        ),
        # Magenta glow layer
        (
            f"drawtext={title_src}:{font_key}='{f_noto}':"
            f"fontsize=120:fontcolor=0xff00aa@0.5:"
            f"x=(w-text_w)/2-7:y=(h-text_h)/2-118-7"
        ),
        # Main white text (on top of glows)
        (
            f"drawtext={title_src}:{font_key}='{f_noto}':"
            f"fontsize=120:fontcolor=white:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-118:"
            f"borderw=3:bordercolor=0xff00aa@0.75:"
            f"shadowx=12:shadowy=12:shadowcolor=0x000000@0.85"
        ),
    ]

    # 11. English channel name in neon cyan
    vf_parts.append(
        f"drawtext=text='VARTA PRAVAH':{font_key}='{f_deja_b}':"
        f"fontsize=62:fontcolor=0x00ffee:"
        f"x=(w-text_w)/2:y=(h-text_h)/2+18:"
        f"borderw=2:bordercolor=0x000000@0.7:"
        f"shadowx=8:shadowy=8:shadowcolor=0x00ffee@0.4"
    )

    # 12. Tagline (muted grey)
    vf_parts.append(
        f"drawtext=text='24x7 AI-Powered Marathi News':{font_key}='{f_deja}':"
        f"fontsize=30:fontcolor=0xaaaaaa:"
        f"x=(w-text_w)/2:y=(h-text_h)/2+94"
    )

    # 13. Pulsing ● LIVE badge (top-left)
    vf_parts.append(
        f"drawtext=text='  LIVE':{font_key}='{f_deja_b}':"
        f"fontsize=28:fontcolor=0xff3333:"
        f"x=28:y=18:"
        f"alpha='0.55+0.45*sin(2*{PI}*T*1.8)':"
        f"borderw=2:bordercolor=white@0.25"
    )

    # 14. "VP" brand badge (top-right)
    vf_parts.append(
        f"drawtext=text='VP':{font_key}='{f_deja_b}':"
        f"fontsize=30:fontcolor=0xff00bb:"
        f"x=iw-66:y=18:"
        f"borderw=2:bordercolor=0xff00bb@0.5"
    )

    # 15. Scrolling ticker
    ticker_src = f"textfile='{ff_path(ticker_file)}'" if ticker_file else "text='Varta Pravah 24x7 Marathi News'"
    vf_parts.append(
        f"drawtext={ticker_src}:{font_key}='{f_deja_b}':"
        f"fontsize=32:fontcolor=white:"
        f"x=w-mod(200*t\\,w+2600):y=ih-63:"
        f"shadowx=2:shadowy=2:shadowcolor=black@0.9"
    )

    vf = ",".join(vf_parts)

    # ── FFmpeg command ─────────────────────────────────────────────
    cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        # Black base — geq paints over it with the animated gradient
        "-f", "lavfi", "-i", "color=c=black:size=1280x720:rate=30",
        # Silent stereo audio (promo has no voice-over)
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", "60",
        "-map", "0:v", "-map", "1:a",
        "-vf", vf,
        # Encode flags — match streamer.py CBR settings so re-encode is lossless
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-r", "30",
        "-g", "60",
        "-keyint_min", "60",
        "-x264opts", "scenecut=0",
        "-pix_fmt", "yuv420p",
        "-b:v", "1000k",
        "-c:a", "aac",
        "-ar", "44100",
        "-b:a", "128k",
        "-ac", "2",
        output_path,
    ]

    result = subprocess.run(cmd, text=True, timeout=600)

    if result.returncode == 0 and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / 1_048_576
        print(f"Gen-Z promo ready: {output_path}  ({size_mb:.1f} MB)")
        # Clear sentinel so ensure_promo_video_activity reuses this file
        try:
            open(sentinel_path, "w").close()
        except Exception:
            pass
        return True
    else:
        print(f"FFmpeg failed (exit {result.returncode})")
        return False


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else None
    ok  = create_genz_promo(out)
    sys.exit(0 if ok else 1)
