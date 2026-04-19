import os
import time
import subprocess
from lip_sync import generate_lipsync

def create_video(data):
    """
    Renders the final news bulletin with a dynamic, scrolling news ticker.
    Input data tuple: (audio_path, ticker_text, anchor_gender, is_breaking)
    """
    audio_path, ticker, anchor, is_breaking = data
    
    # 0. Fetch External Data for Overlays
    from weather import get_weather
    from stocks import get_stocks
    from pulse import get_cricket_score, get_election_updates
    
    weather_text  = get_weather()
    market_text   = get_stocks()
    cricket_text  = get_cricket_score()
    election_text = get_election_updates()
    
    # Merge Stock Market into Ticker
    ticker = f"{market_text} | {ticker}"

    # Apply Breaking News Style
    if is_breaking:
        ticker = "🔴 BREAKING: " + ticker
        box_color = "red@0.8"
    else:
        box_color = "black@0.6"

    # Professional Branding & Audio
    anchor_name = "संवाददाता: क्रितिका" if anchor == "female" else "संवाददाता: प्रियांश"
    lower_text = f"VartaPravah | {anchor_name}"
    logo_path = "/app/assets/logo.png"
    music_path = "/app/assets/news_music.mp3"

    # 1. Unique Output Filename
    ts = int(time.time())
    output = f"/app/videos/news_{ts}.mp4"

    print(f"🎬 [RENDERER] Composite + Audio Mix | Breaking={is_breaking}")

    def escape_ffmpeg_text(text):
        if not text: return ""
        return text.replace("'", "'\\\\\\''").replace(":", "\\\\:")

    # Escape all dynamic text for FFmpeg
    ticker_esc   = escape_ffmpeg_text(ticker)
    lower_esc    = escape_ffmpeg_text(lower_text)
    weather_esc  = escape_ffmpeg_text(weather_text)
    cricket_esc  = escape_ffmpeg_text(cricket_text)
    election_esc = escape_ffmpeg_text(election_text)

    try:
        # 2. Generate Lip-Synced Footage
        lipsync_v = generate_lipsync(audio_path, anchor)

        # 3. FFmpeg Composite
        inputs = [
            "-i", lipsync_v,
            "-i", logo_path
        ]
        
        # Build a robust, single-chain filter complex
        # We start with [0:v] (the lipsync video)
        fc = (
            f"[0:v]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{lower_esc}':x=40:y=h-140:fontsize=32:fontcolor=white:box=1:boxcolor=black@0.7,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{ticker_esc}':x=w-mod(t*150,w+tw):y=h-60:fontsize=28:fontcolor=yellow:box=1:boxcolor={box_color},"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{weather_esc}':x=40:y=40:fontsize=28:fontcolor=cyan:box=1:boxcolor=black@0.5,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "text='%{localtime\\:%H\\\\\\:%M}':x=W-240:y=40:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.5,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{cricket_esc}':x=40:y=120:fontsize=24:fontcolor=white:box=1:boxcolor=red@0.5,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{election_esc}':x=40:y=180:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.5[v_txt];"
            
            # Overlay Logo
            "[1:v]scale=120:120[logo];"
            "[v_txt][logo]overlay=W-160:40[outv]"
        )

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", fc,
            "-map", "[outv]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "128k", "-shortest",
            output
        ]

        subprocess.run(cmd, check=True)
        print(f"✅ [RENDERER] Final Bulletin Ready: {output}")

        # Optional: Cleanup temporary file
        if os.path.exists(lipsync_v) and "lipsync_" in lipsync_v:
            os.remove(lipsync_v)

        return output

    except Exception as e:
        print(f"❌ [RENDERER] Composite failed: {e}")
        return "/app/videos/promo.mp4"
