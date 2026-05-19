import os
from app import config

def create_video(sadtalker_video_path, output_path, script_text=""):
    """
    Generates a professional branded news video.
    Overlays: News Ticker, LIVE Badge, and Channel Logo.
    """
    # ENFORCED STRICT LOGO: The user strictly requested ONLY this logo to be used
    logo_path = os.path.join(config.ASSETS_DIR, "logo.png")

    studio_path = os.path.join(config.ASSETS_DIR, "studio_bg.png")
    font_path = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
    
    # Ensure font exists, try alternate paths
    if not os.path.exists(font_path):
        alt_paths = [
            "/app/assets/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/local/share/fonts/NotoSansDevanagari-Regular.ttf"
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                font_path = alt
                break
        if not os.path.exists(font_path):
            print(f"⚠️ [VIDEO-ENGINE] Devanagari font not found, using system default")
            font_path = "DejaVuSans"

    # Clean text for FFmpeg ticker - preserve Hindi/Devanagari script properly
    # Replace newlines with danda (।) for proper Hindi text flow
    ticker_text = script_text.strip()
    # Remove only problematic quotes, keep Hindi/Devanagari punctuation
    ticker_text = ticker_text.replace('"', '').replace("'", '')
    ticker_text = ticker_text.replace("\n", " | ")
    
    ticker_file = os.path.join(config.OUTPUT_DIR, "ticker.txt")
    with open(ticker_file, "w", encoding="utf-8") as f:
        f.write(ticker_text)

    # FFmpeg Master Filter Complex:
    # 1. Scale Studio to Full 720p Widescreen (Crop-to-Fill)
    # 2. Position Anchor, Logo, and Ticker
    # 3. Overlay visual elements
    master_filter = (
        "[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,format=rgb24[studio];"
        "[1:v]scale=640:-1,format=rgb24[anchor];"
        "[studio][anchor]overlay=(main_w-640)/2:(main_h-480)/2:format=rgb[v1];"
        f"[2:v]scale=250:-1,format=rgba,colorkey=white:0.1:0.2[logo];"
        "[v1][logo]overlay=W-w-30:30:format=rgb[v2];"
        "[v2]drawtext=text='LIVE':fontcolor=white:fontsize=24:x=40:y=40:box=1:boxcolor=red@0.9:boxborderw=10[v3];"
        f"[v3]drawtext=fontfile='{font_path}':textfile='{ticker_file}':fontsize=38:fontcolor=white:x='w-mod(t*80,w+tw)':y='h-75':box=1:boxcolor=black@0.85:boxborderw=12:line_spacing=4,format=yuv420p[vout]"
    )

    # Pre-Flight Check: Verify Assets
    for asset in [logo_path, studio_path, sadtalker_video_path]:
        if not os.path.exists(asset):
            print(f"❌ [VIDEO-ENGINE] Missing Asset: {asset}")
            return None

    tmp_output_path = output_path + ".tmp"
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", studio_path,
        "-i", sadtalker_video_path,
        "-i", logo_path,
        "-filter_complex", master_filter,
        "-map", "[vout]", # Final video
        "-map", "1:a", # Use audio from sadtalker video (input 1)
        "-r", "25", "-s", "1280x720", "-shortest",
        "-c:v", "libx264", "-preset", "fast", "-b:v", "2500k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-f", "mp4",
        tmp_output_path
    ]
    
    print(f"🎬 [VIDEO-ENGINE] Branded Composition: {tmp_output_path}...")
    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ [VIDEO-ENGINE-ERROR] {result.stderr}")
        if os.path.exists(tmp_output_path):
            os.remove(tmp_output_path)
        return None

    os.rename(tmp_output_path, output_path)
    return output_path

class VideoEngine:
    def generate_video(self, video_path, script_text, output_filename):
        output_path = os.path.join(config.OUTPUT_DIR, output_filename)
        return create_video(video_path, output_path, script_text)
