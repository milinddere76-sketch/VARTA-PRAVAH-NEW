import os
import sys
import requests
import json
import time
import uuid
import subprocess
import tempfile
from dotenv import load_dotenv
from temporalio import activity
from groq import Groq
from gtts import gTTS

# Ensure the 'backend' root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from streamer import Streamer
import database
import models

# Initialize AI Clients
load_dotenv()

LANGUAGE_CONFIG = {
    "Marathi": {"code": "mr", "region": "Maharashtra"},
    "Hindi": {"code": "hi", "region": "India"},
    "English": {"code": "en", "region": "India"},
}

STREAMER_INSTANCES: dict[int, Streamer] = {}

def _terminate_stream_process(channel_id: int):
    streamer = STREAMER_INSTANCES.pop(channel_id, None)
    if streamer:
        try:
            streamer.stop_stream()
        except:
            pass
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True)
        else:
            subprocess.run(["pkill", "-9", "-f", "ffmpeg"], capture_output=True)
        print(f"Cleaned up all FFmpeg processes for channel {channel_id}")
    except:
        pass

@activity.defn
async def fetch_news_activity(language: str) -> dict:
    load_dotenv(override=True)
    api_key = os.getenv("WORLD_NEWS_API_KEY")
    lang_code = LANGUAGE_CONFIG.get(language, {"code": "hi"})["code"]
    combined_headline = "Top Updates: "
    combined_description = ""
    priorities = [("Maharashtra", 3), ("India", 3), ("World", 2)]
    for category, count in priorities:
        url = f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text={category}&language={lang_code}&number={count}"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("news"):
                for n in data["news"]:
                    combined_headline += f" | {n['title']}"
                    combined_description += f"\n[{category.upper()} NEWS]: {n['text'][:250]}..."
        except Exception: pass
    if not combined_description:
        combined_headline = "Varta Pravah Morning Updates | "
        combined_description = "Namaskar, Maharashtra. Aajchya thak batmya."
    return {"headline": combined_headline, "description": combined_description}

@activity.defn
async def generate_script_activity(input_data: dict) -> dict:
    load_dotenv(override=True)
    news_data = input_data["news_data"]
    is_female = input_data.get("is_female", False)
    anchor_name = "Priya Desai" if is_female else "Arjun Sharma"
    system_prompt = f"""You are the lead scriptwriter for 'VARTA PRAVAH', Maharashtra's #1 Marathi News Channel.
    Write a news script in PURE PROFESSIONAL MARATHI (Devanagari).
    Start with: 'Namaskar, Varta Pravah madhe aaple swagat aahe. Me {anchor_name}, aajchya thak batmya gheun yet aahe.'
    Rules: Formal tone. No English for news terms. Marathi script only."""
    user_prompt = f"HEADLINE: {news_data['headline']}\nDESCRIPTION: {news_data['description']}"
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0.3)
        script = completion.choices[0].message.content
        return {"script": script, "is_female": is_female}
    except Exception:
        return {"script": f"Namaskar, Varta Pravah madhe aaple swagat aahe. Me {anchor_name}. Aajchya thak batmya. Dhanyavad.", "is_female": is_female}

@activity.defn
async def generate_audio_activity(input_data: dict) -> str:
    script = input_data.get("script", "")
    audio_path = os.path.join(tempfile.gettempdir(), f"news_{uuid.uuid4().hex}.mp3")
    try:
        tts = gTTS(text=script, lang="mr")
        tts.save(audio_path)
        return audio_path
    except Exception:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "10", "-c:a", "libmp3lame", audio_path], capture_output=True)
        return audio_path

@activity.defn
async def generate_news_video_activity(input_data: dict) -> str:
    from PIL import Image, ImageDraw, ImageFont
    title = input_data.get("title", "Breaking News")
    audio_path = input_data.get("audio_url", "")
    from database import SessionLocal
    from models import Channel, Anchor
    db = SessionLocal()
    channel = db.query(Channel).first()
    anchor = db.query(Anchor).filter(Anchor.id == channel.preferred_anchor_id).first() if channel else None
    db.close()
    assets_dir = os.path.join(BASE_DIR, "assets")
    bg_p = os.path.join(assets_dir, "studio_bg.png")
    logo_p = os.path.join(assets_dir, "logo.png")
    port_p = os.path.join(BASE_DIR, anchor.portrait_url) if anchor and anchor.portrait_url else os.path.join(assets_dir, "female_anchor.png")
    try:
        studio = Image.open(bg_p).convert("RGBA").resize((1920, 1080)) if os.path.exists(bg_p) else Image.new("RGBA", (1920, 1080), (15, 25, 45, 255))
        if os.path.exists(port_p):
            port = Image.open(port_p).convert("RGBA")
            p_w = 1000
            p_h = int(port.height * (p_w / port.width))
            port = port.resize((p_w, p_h))
            studio.paste(port, (1920 - p_w - 50, 1080 - p_h), port)
        if os.path.exists(logo_p):
            logo = Image.open(logo_p).convert("RGBA").resize((220, 220))
            studio.paste(logo, (1920 - 280, 50), logo)
        draw = ImageDraw.Draw(studio)
        draw.rectangle([0, 960, 1920, 1080], fill=(0, 0, 150, 240))
        draw.rectangle([0, 950, 1920, 960], fill=(0, 180, 255, 255))
        draw.rectangle([0, 960, 350, 1080], fill=(200, 0, 0, 255))
        try:
            # Dynamic Font Discovery for Devanagari (Marathi)
            font_candidates = [
                "C:/Windows/Fonts/Nirmala.ttf",
                "C:/Windows/Fonts/Mangal.ttf",
                "C:/Windows/Fonts/Kokila.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
                "C:/Windows/Fonts/arial.ttf"
            ]
            font_t = None
            for fp in font_candidates:
                if os.path.exists(fp):
                    try:
                        font_t = ImageFont.truetype(fp, 45)
                        break
                    except: continue
            if not font_t: font_t = ImageFont.load_default()
        except: font_t = ImageFont.load_default()
        draw.text((40, 985), "ताज्या बातम्या", font=font_t, fill=(255, 255, 255))
        draw.text((380, 985), title[:70], font=font_t, fill=(255, 255, 255))
        frame_p = os.path.join(tempfile.gettempdir(), "studio.png")
        studio.save(frame_p)
        out_p = os.path.join(BASE_DIR, "videos", "news_generated.mp4")
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", frame_p, "-i", audio_path, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out_p], check=True)
        return out_p
    except Exception as e:
        print(f"Render Error: {e}")
        return os.path.join(BASE_DIR, "videos", "promo.mp4")

@activity.defn
async def ensure_promo_video_activity(channel_id: int = 1) -> bool:
    promo_p = os.path.join(BASE_DIR, "videos", "promo.mp4")
    return os.path.exists(promo_p)

@activity.defn
async def start_stream_activity(data: dict) -> str:
    c_id, s_key, v_url = data["channel_id"], data["stream_key"], data["video_url"]
    _terminate_stream_process(c_id)
    time.sleep(2)
    try:
        if not os.path.isabs(v_url): v_url = os.path.join(BASE_DIR, v_url)
        if not os.path.exists(v_url) or os.path.getsize(v_url) < 10000: v_url = os.path.join(BASE_DIR, "videos", "promo.mp4")
        streamer = Streamer(s_key, c_id)
        streamer.create_initial_playlist(v_url)
        streamer.start_stream()
        STREAMER_INSTANCES[c_id] = streamer
        return "stream_started"
    except Exception: return "failed"

@activity.defn
async def stop_stream_activity(channel_id: int) -> str:
    _terminate_stream_process(channel_id)
    return "stopped"

@activity.defn
async def check_scheduled_ads_activity(data: dict) -> list[str]: return []

@activity.defn
async def cleanup_old_videos_activity() -> str: return "Cleanup skipped"

@activity.defn
async def ensure_premium_promo_activity() -> bool: return True

@activity.defn
async def get_channel_anchor_activity(channel_id: int) -> dict: return {"gender": "female", "name": "Priya"}

@activity.defn
async def upload_to_s3_activity(v_url: str) -> str: return v_url

@activity.defn
async def synclabs_lip_sync_activity(data: dict) -> str: return "mock_job"

@activity.defn
async def check_sync_labs_status_activity(job_id: str) -> dict: return {"status": "completed", "video_url": ""}
