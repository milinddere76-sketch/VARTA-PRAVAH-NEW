import os
from app import config

def create_video(sadtalker_video_path, output_path, script_text=""):
    """
    Generates a professional branded news video.
    Overlays: News Ticker, LIVE Badge, and Channel Logo.
    """
    # LOGO-HUNTER: Search for every possible logo name to ensure branding uptime
    logo_path = os.path.join(config.ASSETS_DIR, "logo.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(config.ASSETS_DIR, "varta_logo.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(config.ASSETS_DIR, "promo_1.png") # Ultimate fallback
        
    studio_path = os.path.join(config.ASSETS_DIR, "studio_bg.png")
    font_path = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
    
    if not os.path.exists(font_path):
        font_path = "DejaVu Sans"

    # Clean text for FFmpeg (The Ultimate Shield)
    ticker_text = script_text.replace("\n", " | ").replace("'", "").replace("\"", "")
    ticker_file = os.path.join(config.OUTPUT_DIR, "ticker.txt")
    with open(ticker_file, "w", encoding="utf-8") as f:
        f.write(ticker_text)

    # FFmpeg Master Filter Complex:
    # 1. Scale Studio to Full 720p Widescreen (Crop-to-Fill)
    # 2. Position Anchor, Logo, and Ticker
    # 3. Mix Speech and Background Music
    master_filter = (
        "[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720[studio];"
        "[1:v]scale=720:-1[anchor];"
        "[studio][anchor]overlay=(main_w-720)/2:(main_h-720)/2+50[v1];"
        f"[2:v]scale=180:-1[logo];"
        "[v1][logo]overlay=W-w-30:30[v2];"
        "[v2]drawtext=text='LIVE':fontcolor=white:fontsize=24:x=40:y=40:box=1:boxcolor=red@0.9:boxborderw=10[v3];"
        f"[v3]drawtext=fontfile='{font_path}':textfile='{ticker_file}':x='w-mod(t*200,w+tw)':y='h-100':fontsize=45:fontcolor=white:box=1:boxcolor=black@0.8:boxborderw=20[vout];"
        "[1:a][3:a]amix=inputs=2:duration=first:dropout_transition=2[aout]"
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
        "-f", "lavfi", "-i", "sine=f=80:d=1,aecho=0.8:0.88:60:0.4", # Input 3: News Bed
        "-filter_complex", master_filter,
        "-map", "[vout]", # Final video
        "-map", "[aout]", # Final mixed audio
        "-r", "25", "-s", "1280x720", "-shortest",
        "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "2500k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
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
