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
import edge_tts
import asyncio

# --- CONSTANTS ---
BASE_DIR = "/app"
VIDEOS_DIR = "/app/videos"
PROMO_PATH = "/app/videos/promo.mp4"

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
    try:
        # Standard FFmpeg cleanup to prevent overlaps
        if sys.platform != "win32":
            subprocess.run(["pkill", "-9", "-f", "ffmpeg"], capture_output=True)
            subprocess.run(["pkill", "-9", "-f", "gapless_streamer.py"], capture_output=True)
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
    show_greeting = input_data.get("show_greeting", True)
    
    # Time-aware greeting (IST)
    import datetime
    from zoneinfo import ZoneInfo
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    
    # Only use greeting if it's the start of the bulletin
    if show_greeting:
        if 5 <= now_ist.hour < 12:
            greeting = f"नमस्कार, शुभ प्रभात! आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} सकाळच्या प्रमुख घडामोडी. चला पाहूया आजच्या दिवसाची सुरुवात करणाऱ्या महत्त्वाच्या बातम्या."
        elif 12 <= now_ist.hour < 17:
            greeting = f"नमस्कार! आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} दुपारच्या ताज्या अपडेट्स. चला जाणून घेऊया आतापर्यंतच्या महत्त्वाच्या बातम्या."
        elif 17 <= now_ist.hour < 20:
            greeting = f"नमस्कार! आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} दिवसभरातील महत्त्वाच्या घडामोडी. चला पाहूया संध्याकाळच्या प्रमुख बातम्या."
        elif 20 <= now_ist.hour < 22:
            greeting = f"नमस्कार! आपण पाहत आहात 'वार्ताप्रवाह' — सत्याचा आरसा. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} आजच्या दिवसातील सर्वात मोठ्या आणि परिणामकारक बातम्या. सुरुवात करूया हेडलाईन्सने."
        else:
            greeting = f"नमस्कार! आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} दिवसभराचा संक्षिप्त आढावा. चला पाहूया आजच्या मुख्य बातम्या."
    else:
        # Standard inner-bulletin transition
        greeting = f"पुढील महत्त्वाची बातमी समोर येत आहे..."

    system_prompt = f"""You are a Marathi News Scholar for 'VARTA PRAVAH'. 
    TONE: Neutral, Professional, Authoritative. NO DRAMA.
    
    STRICT STRUCTURE:
    1. OPENING: Start with: '{greeting}'
    2. BREAKING HOOK: Say: 'थांबा जरा! एक मोठी ब्रेकिंग न्यूज समोर येत आहे…'
    3. CONTENT: 6-8 professional Marathi sentences (Shuddha Marathi). This should take ~25 seconds to speak.
    4. TAGLINE: Finish with: 'सत्य, वेग आणि विश्वासाचा प्रवाह. पाहत रहा, वार्ताप्रवाह. धन्यवाद.'
    
    GENDER RULES: Anchor is {anchor_name} | Use '{'आले आहे' if is_female else 'आलो आहे'}'.
    LINGUISTIC: Devanagari ONLY. NO Roman/English characters."""
    user_prompt = f"IF THE FOLLOWING NEWS IS IN ENGLISH, TRANSLATE IT TO PURE MARATHI FIRST AND THEN WRITE THE SCRIPT.\nHEADLINE: {news_data['headline']}\nDESCRIPTION: {news_data['description']}"
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0.3)
        script = completion.choices[0].message.content
        print(f"--- [VERIFICATION] News Script Generated ---")
        print(f"Anchor: {anchor_name} | Language: Marathi")
        print(f"Script Context:\n{script[:200]}...")
        print(f"-------------------------------------------")
        return {"script": script, "is_female": is_female}
    except Exception as e:
        print(f"Groq Script Error: {e}")
        return {"script": f"Namaskar, Varta Pravah madhe aaple swagat aahe. Me {anchor_name}. Aajchya thak batmya. Dhanyavad.", "is_female": is_female}

@activity.defn
async def generate_headlines_activity(input_data: dict) -> dict:
    news_items = input_data["news_items"]
    is_female = input_data.get("is_female", False)
    anchor_name = "Priya Desai" if is_female else "Arjun Sharma"

    import datetime
    from zoneinfo import ZoneInfo
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    
    if 5 <= now_ist.hour < 12: greeting = f"नमस्कार, शुभ प्रभात! आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} सकाळच्या प्रमुख घडामोडी. सुरुवात करूया मुख्य हेडलाईन्सने."
    elif 12 <= now_ist.hour < 17: greeting = f"नमस्कार! आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} दुपारच्या ताज्या अपडेट्स. सुरुवात करूया मुख्य हेडलाईन्सने."
    elif 17 <= now_ist.hour < 20: greeting = f"नमस्कार! आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} दिवसभरातील महत्त्वाच्या घडामोडी. सुरुवात करूया मुख्य हेडलाईन्सने."
    elif 20 <= now_ist.hour < 22: greeting = f"नमस्कार! आपण पाहत आहात 'वार्ताप्रवाह' — सत्याचा आरसा. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} आजच्या दिवसातील सर्वात मोठ्या आणि परिणामकारक बातम्या. सुरुवात करूया हेडलाईन्सने."
    else: greeting = f"नमस्कार! आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, घेऊन {'आले आहे' if is_female else 'आलो आहे'} दिवसभराचा संक्षिप्त आढावा. सुरुवात करूया मुख्य हेडलाईन्सने."

    headlines_text = "\n".join([f"- {item['headline']}" for item in news_items[:5]])
    
    system_prompt = f"You are a Marathi News Anchor for 'VARTA PRAVAH'. Write a FAST-PACED headlines segment.\n" \
                    f"1. Start with exactly: '{greeting}'\n" \
                    f"2. Read the following 5 headlines in impactful, short Marathi sentences.\n" \
                    f"3. Use a bullet-point style delivery ('पहिली मोठी बातमी...', 'दुसरीकडे...', 'तसेच...').\n" \
                    f"4. Suffix each headline with energy. Finish with: 'आता पाहूया सविस्तर बातम्या.'\n" \
                    f"TONE: High-energy, professional, Devanagari ONLY."
    
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": headlines_text}], temperature=0.3)
        return {"script": completion.choices[0].message.content, "is_female": is_female}
    except:
        return {"script": f"{greeting} ठळक बातम्या. सविस्तर बातम्या आता पाहूया.", "is_female": is_female}

@activity.defn
async def generate_closing_activity(input_data: dict) -> dict:
    is_female = input_data.get("is_female", False)
    
    script = "ही होती आजच्या प्रमुख बातम्यांची झलक. अधिक अपडेट्ससाठी पाहत राहा 'वार्ताप्रवाह' — सत्य, वेग आणि विश्वासाचा प्रवाह. नमस्कार!"
    
    return {"script": script, "is_female": is_female}

@activity.defn
async def generate_audio_activity(input_data: dict) -> str:
    script = input_data.get("script", "")
    is_female = input_data.get("is_female", True)
    audio_path = os.path.join(tempfile.gettempdir(), f"news_{uuid.uuid4().hex}.mp3")
    
    # Professional Marathi voices from Microsoft Edge TTS
    voice = "mr-IN-AarohiNeural" if is_female else "mr-IN-ManoharNeural"
    
    try:
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(audio_path)
        return audio_path
    except Exception as e:
        print(f"Edge TTS Error: {e}")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "10", "-c:a", "libmp3lame", audio_path], capture_output=True)
        return audio_path

@activity.defn
async def generate_news_video_activity(input_data: dict) -> str:
    from PIL import Image, ImageDraw, ImageFont
    title = input_data.get("title", "Breaking News")
    audio_path = input_data.get("audio_url", "")
    synced_v = input_data.get("synced_video_url", "")
    
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
        
        # Static portrait only if NOT using lip-sync video
        if not synced_v and os.path.exists(port_p):
            port = Image.open(port_p).convert("RGBA")
            p_w = 950
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

        # Font discovery for Marathi
        font_t = ImageFont.load_default()
        for fp in ["C:/Windows/Fonts/Nirmala.ttf", "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", "arial.ttf"]:
            if os.path.exists(fp):
                try: font_t = ImageFont.truetype(fp, 45); break
                except: continue

        draw.text((40, 985), "ताज्या बातम्या", font=font_t, fill=(255, 255, 255))
        draw.text((380, 985), title[:70], font=font_t, fill=(255, 255, 255))
        
        frame_p = os.path.join(tempfile.gettempdir(), "studio_base.png")
        studio.save(frame_p)
        
        out_p = os.path.join(BASE_DIR, "videos", "news_generated.mp4")
        
        if synced_v:
            # Composite talking anchor video onto studio background
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", frame_p,
                "-i", synced_v,
                "-filter_complex", 
                "[1:v]scale=950:-1[anchor];[0:v][anchor]overlay=1920-950-50:H-h[outv]",
                "-map", "[outv]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-shortest", out_p
            ]
        else:
            ffmpeg_cmd = ["ffmpeg", "-y", "-loop", "1", "-i", frame_p, "-i", audio_path, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out_p]
        
        subprocess.run(ffmpeg_cmd, check=True)
        return out_p
    except Exception as e:
        print(f"Render Error: {e}")
        return os.path.join(BASE_DIR, "videos", "promo.mp4")

from create_premium_promo import create_premium_promo

@activity.defn
async def ensure_premium_promo_activity() -> bool:
    promo_p = os.path.join(BASE_DIR, "videos", "promo.mp4")
    if not os.path.exists(promo_p) or os.path.getsize(promo_p) < 100000:
        print("🎬 Generating NEW Premium Promo...")
        try:
            create_premium_promo(promo_p)
            return True
        except Exception as e:
            print(f"❌ Promo Generation Failed: {e}")
            return False
    return True

@activity.defn
async def ensure_promo_video_activity(channel_id: int = 1) -> bool:
    return await ensure_premium_promo_activity()

@activity.defn
async def start_stream_activity(data: dict) -> str:
    c_id, s_key, v_url = data["channel_id"], data["stream_key"], data["video_url"]
    
    # 1. Resolve Path
    if not os.path.isabs(v_url): v_url = os.path.join(BASE_DIR, v_url)
    if not os.path.exists(v_url) or os.path.getsize(v_url) < 10000: 
        v_url = os.path.join(BASE_DIR, "videos", "promo.mp4")

    # 2. SEAMLESS SWIPE (Symlink Switch)
    live_symlink = os.path.join(BASE_DIR, "videos", "current_live.mp4")
    try: 
        if os.path.exists(live_symlink) or os.path.islink(live_symlink): os.remove(live_symlink)
        os.symlink(v_url, live_symlink)
        print(f"🔄 [LIVE] Switched stream source to: {v_url}")
    except Exception as e:
        print(f"⚠️ [LIVE] Symlink failed: {e}")

    # 3. Ensure the Continuous Ingest is running
    # If already running, FFmpeg will see the playlist update on next loop.
    # If NOT running, we start it in the background.
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{s_key}"
    
    # Check if a gapless streamer is already alive
    check_cmd = ["pgrep", "-f", f"gapless_streamer.py.*{s_key[:5]}"]
    if sys.platform == "win32": check_cmd = ["tasklist"] # simplified
    
    res = subprocess.run(check_cmd, capture_output=True)
    if b"gapless_streamer" not in res.stdout:
        print(f"📡 [GHOST] Launching Permanent 24/7 Ingest for Channel {c_id}")
        subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "gapless_streamer.py"), rtmp_url, v_url])
        
    return "gapless_switch_complete"

@activity.defn
async def stop_stream_activity(channel_id: int) -> str:
    _terminate_stream_process(channel_id)
    return "stopped"

@activity.defn
async def check_scheduled_ads_activity(data: dict) -> list[str]: return []

@activity.defn
async def cleanup_old_videos_activity() -> str: return "Cleanup skipped"



@activity.defn
async def get_channel_anchor_activity(channel_id: int) -> dict: return {"gender": "female", "name": "Priya"}

@activity.defn
async def upload_to_s3_activity(v_url: str) -> str: return v_url

@activity.defn
async def synclabs_lip_sync_activity(data: dict) -> str:
    """Sends audio and gender-appropriate base video to Sync Labs for lip-sync."""
    api_key = os.getenv("SYNCLABS_API_KEY")
    if not api_key: return "no_api_key"
    
    is_female = data.get("is_female", True)
    # Target high-quality base videos matching the anchor gender
    # These base videos should be clean segments of the specific anchor models
    base_video = os.getenv("SYNC_LABS_FEMALE_VIDEO") if is_female else os.getenv("SYNC_LABS_MALE_VIDEO")
    
    if not base_video:
        # Fallback to predefined public assets if env vars aren't set
        base_video = "https://storage.googleapis.com/varta-pravah/female_anchor_clean.mp4" if is_female else "https://storage.googleapis.com/varta-pravah/male_anchor_clean.mp4"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "audioUrl": data['audio_url'], 
        "videoUrl": base_video,
        "synergize": True
    }
    try:
        r = requests.post("https://api.synclabs.so/v2/lipsync", headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        return r.json().get("id")
    except Exception as e:
        print(f"SyncLabs Request Failed: {e}")
        return "failed"

@activity.defn
async def check_sync_labs_status_activity(job_id: str) -> dict:
    """Polls Sync Labs for the finished lip-synced video."""
    if job_id in ["no_api_key", "failed"]: 
        return {"status": "completed", "video_url": ""}
    
    api_key = os.getenv("SYNCLABS_API_KEY")
    headers = {"x-api-key": api_key}
    try:
        r = requests.get(f"https://api.synclabs.so/v2/lipsync/{job_id}", headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {
            "status": data.get("status"),
            "video_url": data.get("videoUrl") if data.get("status") == "completed" else ""
        }
    except Exception as e:
        print(f"SyncLabs Polling Failed: {e}")
        return {"status": "failed"}
