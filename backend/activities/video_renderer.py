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
    
    # Apply Breaking News Style
    if is_breaking:
        ticker = "🔴 BREAKING: " + ticker
        box_color = "red@0.8"
    else:
        box_color = "black@0.6"

    # Professional Branding & Audio
    anchor_name = "अँकर: क्रितिका" if anchor == "female" else "अँकर: प्रियांश"
    lower_text = f"VartaPravah | {anchor_name}"
    logo_path = "/app/assets/logo.png"
    music_path = "/app/assets/news_music.mp3"

    # 1. Unique Output Filename
    ts = int(time.time())
    output = f"/app/videos/news_{ts}.mp4"

    print(f"🎬 [RENDERER] Composite + Audio Mix | Breaking={is_breaking}")

    try:
        # 2. Generate Lip-Synced Footage
        lipsync_v = generate_lipsync(audio_path, anchor)

        # 3. FFmpeg Composite with High-End TV Branding & Audio Mix
        inputs = [
            "-i", "/app/videos/studio.mp4",
            "-i", lipsync_v,
            "-i", logo_path
        ]
        
        # Add music if it exists
        has_music = os.path.exists(music_path)
        if has_music:
            inputs.extend(["-i", music_path])

        filter_complex = (
            "[0:v]scale=854:480[bg];"
            "[1:v]scale=270:405[anchor];"
            "[bg][anchor]overlay=30:65[tmp1];"
            "[tmp1]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{lower_text}':x=15:y=h-100:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.7[tmp2];"
            "[tmp2][2:v]scale=80:80[logo];"
            "[tmp2][logo]overlay=W-100:20[tmp3];"
            "[tmp3]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{ticker}':x=w-mod(t*150,w+tw):y=h-40:fontsize=20:fontcolor=yellow:box=1:boxcolor={box_color},fade=t=in:st=0:d=1[outv]"
        )

        if has_music:
            filter_complex += ";[3:a]volume=0.3[music];[1:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]"
            map_audio = "[outa]"
        else:
            map_audio = "1:a"

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", map_audio,
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "128k", "-shortest",
            output
        ]

        subprocess.run(cmd, check=True)
        print(f"✅ [RENDERER] Video with Scrolling Ticker ready: {output}")

        # Optional: Cleanup temporary file
        if os.path.exists(lipsync_v) and "lipsync_" in lipsync_v:
            os.remove(lipsync_v)

        return output

    except Exception as e:
        print(f"❌ [RENDERER] Composite failed: {e}")
        return "/app/videos/promo.mp4"
