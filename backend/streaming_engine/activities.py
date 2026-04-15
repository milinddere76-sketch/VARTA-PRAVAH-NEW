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
import datetime

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
async def fetch_news_activity(language: str) -> list[dict]:
    load_dotenv(override=True)
    api_key = os.getenv("WORLD_NEWS_API_KEY")
    lang_code = LANGUAGE_CONFIG.get(language, {"code": "mr"})["code"]
    
    from database import SessionLocal
    from models import News
    db = SessionLocal()
    
    # Get existing headlines from last 24h to avoid duplicates
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    existing_headlines = {n.headline for n in db.query(News).filter(News.created_at >= yesterday).all()}
    
    results = []
    queries = [
        ("Maharashtra", 15),
        ("India", 10),
        ("World News", 5)
    ]
    
    for query, count in queries:
        url = f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text={query}&language={lang_code}&number={count}"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if data.get("news"):
                for n in data["news"]:
                    title = n.get("title", "")
                    if title and title not in existing_headlines:
                        news_item = {
                            "id": n.get("id") or uuid.uuid4().hex[:8],
                            "headline": title,
                            "description": n.get("text", "")[:800]
                        }
                        results.append(news_item)
                        # Persist to DB immediately
                        db_news = News(headline=title, description=news_item["description"], language=language)
                        db.add(db_news)
                        existing_headlines.add(title)
        except: continue
        if len(results) >= 25: break

    db.commit()
    db.close()
    
    # FALLBACK
    if not results:
        results = [
            {"headline": "महाराष्ट्रातील ताज्या घडामोडी", "description": "राज्यातील राजकीय आणि सामाजिक घडामोडींचा आढावा लवकरच सविस्तर स्वरूपात."},
            {"headline": "मुंबईची जीवनवाहिनी सुरळीत", "description": "मध्य आणि पश्चिम रेल्वेच्या लोकल फेऱ्या वेळेवर धावत आहेत."},
            {"headline": "पुण्यातील हवामान अपडेट", "description": "पुणे शहरात पुढील २४ तासांत पावसाची शक्यता वर्तवण्यात आली आहे."}
        ]
    
    return results[:25]

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
    bulletin_type = input_data.get("bulletin_type", "Standard")
    anchor_name   = "Priya Desai" if is_female else "Arjun Sharma"

    import datetime
    from zoneinfo import ZoneInfo
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    
    # Custom Slot Logic
    if "Morning" in bulletin_type: 
        greeting = f"सकाळच्या ताज्या घडामोडींमध्ये आपले स्वागत..."
        focus = "Focus on overnight developments, weather, and traffic updates."
    elif "Prime" in bulletin_type:
        greeting = f"आजच्या प्राइमिटाईम विशेष चर्चेत आपले स्वागत..."
        focus = "Provide deep analysis, debate-style counter-points, and impact assessment."
    elif "Afternoon" in bulletin_type:
        greeting = f"दुपारच्या या सत्रात पाहूया आतापर्यंतच्या मोठ्या बातम्या..."
        focus = "Focus on politics, economy, and local Maharashtra updates."
    else:
        greeting = f"पुढील महत्त्वाची बातमी समोर येत आहे..."
        focus = "Standard professional reporting."

    system_prompt = f"""You are a Distinguished Marathi News Journalist for 'VARTA PRAVAH'. 
    TONE: Professional, Authoritative, Shuddha Marathi.
    SLOT FOCUS: {focus}
    
    STRICT STRUCTURE:
    1. OPENING: Start with: '{greeting if show_greeting else 'पुढची बातमी...'}'
    2. CONTENT: 6-8 comprehensive Marathi sentences. Use sophisticated vocabulary.
    3. TAGLINE: Finish with: 'पाहत राहा, वार्ताप्रवाह. धन्यवाद.'
    
    GENDER RULES: Anchor is {anchor_name} | Use correct gendered grammar.
    LINGUISTIC: Devanagari ONLY."""
    
    user_prompt = f"WRITE NEWS FOR: {news_data['headline']}\nDETAILS: {news_data['description']}"
    
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0.3)
        script = completion.choices[0].message.content
        return {"script": script, "is_female": is_female}
    except Exception as e:
        print(f"Script Generation Failed: {e}")
        return {"script": f"नमस्कार, वार्ताप्रवाहमध्ये आपले स्वागत. ताजी बातमी आहे - {news_data['headline']}. सविस्तर वृत्त लवकरच.", "is_female": is_female}
        return {"script": f"Namaskar, Varta Pravah madhe aaple swagat aahe. Me {anchor_name}. Aajchya thak batmya. Dhanyavad.", "is_female": is_female}

@activity.defn
async def generate_headlines_activity(input_data: dict) -> dict:
    news_items = input_data["news_items"]
    is_female = input_data.get("is_female", True)
    voice = "mr-IN-AarohiNeural" if is_female else "mr-IN-ManoharNeural"
    
    print(f"--- [TTS] Generating Audio ({'Female' if is_female else 'Male'}) ---")
    from zoneinfo import ZoneInfo
    import datetime
    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    bulletin_type = input_data.get("bulletin_type", "Standard")
    anchor_name = "Priya Desai" if is_female else "Arjun Sharma"
    
    # Context-aware greetings based on User Schedule
    if "Morning" in bulletin_type:
        greeting = f"नमस्कार, शुभ प्रभात! आपण पाहत आहात 'सकाळच्या बातम्या'. मी {anchor_name}, घेऊन आले आहे आजच्या मुख्य घडामोडी आणि रात्रभराचे अपडेट्स."
    elif "Prime" in bulletin_type:
        greeting = f"नमस्कार, आपण पाहत आहात 'प्राइम टाइम विशेष'. मी {anchor_name}, आजच्या दिवसातील 'Top 10' मोठ्या बातम्यांचे सविस्तर विश्लेषण घेऊन आले आहे."
    elif "Night" in bulletin_type:
        greeting = f"शुभ रात्री. आपण पाहत आहात 'रात्रीच्या बातम्या'. मी {anchor_name}, दिवसभराचा संपूर्ण आढावा घेऊन आले आहे."
    else:
        greeting = f"नमस्कार, आपण पाहत आहात 'वार्ताप्रवाह'. मी {anchor_name}, या वेळच्या प्रमुख बातम्यांसह."

    headlines_text = "\n".join([f"- {item['headline']}" for item in news_items[:5]])
    
    system_prompt = f"You are a Senior Marathi News Editor for 'VARTA PRAVAH'. Write a {bulletin_type} headlines segment.\n" \
                    f"PERSONA: {anchor_name} | GENDER: {'Female' if is_female else 'Male'}\n" \
                    f"RULE 1: Start with: '{greeting}'\n" \
                    f"RULE 2: Use impact-heavy Marathi words (e.g., 'खळबळजनक', 'ऐतिहासिक', 'कठोर पाऊल').\n" \
                    f"RULE 3: Professional News Tone. Devanagari ONLY."
    
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
    audio_path = os.path.join(VIDEOS_DIR, f"news_{uuid.uuid4().hex}.mp3")
    
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
    
    is_female = input_data.get("is_female", True)
    
    from database import SessionLocal
    from models import Channel, Anchor
    db = SessionLocal()
    # Find a matching anchor by gender
    anchor = db.query(Anchor).filter(Anchor.gender == ("female" if is_female else "male")).first()
    db.close()

    assets_dir = os.path.join(BASE_DIR, "assets")
    bg_p = os.path.join(assets_dir, "studio_bg.png")
    logo_p = os.path.join(assets_dir, "logo.png")
    
    default_port = "female_anchor.png" if is_female else "male_anchor.png"
    port_p = os.path.join(BASE_DIR, anchor.portrait_url) if anchor and anchor.portrait_url else os.path.join(assets_dir, default_port)

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
        
        frame_p = os.path.join(VIDEOS_DIR, "studio_base.png")
        studio.save(frame_p)
        
        # Use unique filename to prevent overwriting files while streamer is reading them
        file_id = uuid.uuid4().hex[:8]
        out_p = os.path.join(BASE_DIR, "videos", f"news_{file_id}.mp4")
        
        if synced_v:
            # Composite talking anchor video onto studio background
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", frame_p,
                "-i", synced_v,
                "-filter_complex", 
                "[1:v]scale=950:-1[anchor];[0:v][anchor]overlay=1920-950-50:H-h[outv];"
                "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[aout]",
                "-map", "[outv]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-shortest", out_p
            ]
        else:
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", frame_p,
                "-i", audio_path,
                "-filter_complex", "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-shortest", out_p
            ]
        
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
    
    # 1. Path & Key Normalization
    live_symlink = "/app/videos/current_live.mp4"
    if not s_key or len(s_key) < 5:
        s_key = os.getenv("YOUTUBE_STREAM_KEY")
    
    if not s_key:
        print("❌ No stream key available")
        return "failed"

    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{s_key}"

    # 2. SEAMLESS SWIPE (Update the target)
    if os.path.exists(v_url) and os.path.getsize(v_url) > 1000:
        target = v_url
    else:
        target = "/app/videos/promo.mp4"

    try:
        if os.path.exists(live_symlink) or os.path.islink(live_symlink): os.remove(live_symlink)
        os.symlink(target, live_symlink)
        print(f"🔄 [LIVE] Hot-Swapped stream to: {target}")
    except Exception as e:
        print(f"⚠️ [LIVE] Swap failed: {e}")

    # 3. Ensure a SINGLE Gapless Engine is alive (Kill any duplicates)
    print("🧹 [SWEEP] Flushing stale streamer processes...")
    subprocess.run(["pkill", "-9", "-f", "gapless_streamer.py"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", "GAPLESS_STREAMER"], capture_output=True)
    time.sleep(1) # Wait for port/socket release
    
    print(f"📡 [INGEST] Launching Fresh Permanent 24/7 Engine for Ch {c_id}")
    log_f = open("/app/videos/streamer_output.log", "a")
    proc = subprocess.Popen(
        [sys.executable, "/app/gapless_streamer.py", rtmp_url, live_symlink],
        stdout=log_f,
        stderr=log_f,
        start_new_session=True
    )
    print(f"📡 [INGEST] Process launched with PID {proc.pid}")
    
    return "switch_complete"

@activity.defn
async def stop_stream_activity(channel_id: int) -> str:
    _terminate_stream_process(channel_id)
    return "stopped"

@activity.defn
async def check_scheduled_ads_activity(data: dict) -> list[str]: return []

@activity.defn
async def merge_videos_activity(video_paths: list[str]) -> str:
    """Merges multiple MP4 clips into a single bulletin using FFmpeg concat demuxer."""
    if not video_paths: return ""
    if len(video_paths) == 1: return video_paths[0]
    
    output_path = os.path.join(VIDEOS_DIR, f"bulletin_{uuid.uuid4().hex[:8]}.mp4")
    
    # Create concat list file
    list_file = os.path.join(VIDEOS_DIR, f"concat_{uuid.uuid4().hex[:8]}.txt")
    with open(list_file, "w") as f:
        for p in video_paths:
            # Ensure path is absolute for internal Docker context
            abs_p = p if p.startswith("/") else os.path.join(BASE_DIR, p)
            if os.path.exists(abs_p):
                f.write(f"file '{abs_p}'\n")

    # Perform fast stream-copy merge
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", output_path
    ]
    try:
        subprocess.run(cmd, check=True)
        return output_path
    except Exception as e:
        print(f"Merge Failed: {e}")
        return video_paths[0]

@activity.defn
async def cleanup_old_videos_activity() -> str: 
    """Purges news and bulletin files older than 24 hours to save disk space."""
    import time
    now = time.time()
    count = 0
    for f in os.listdir(VIDEOS_DIR):
        if f.startswith("news_") or f.startswith("bulletin_"):
            p = os.path.join(VIDEOS_DIR, f)
            if os.path.getmtime(p) < (now - 86400):
                os.remove(p)
                count += 1
    return f"Cleaned {count} files"



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
        "x-api-key": api_key
    }
    
    # Check if audio_url is a local file or a URL
    audio_path = data.get('audio_url', '')
    payload = {"model": "lipsync-2"}
    
    try:
        if audio_path.startswith("http"):
            # URL Based
            payload["input"] = [
                {"type": "video", "url": base_video},
                {"type": "audio", "url": audio_path}
            ]
            r = requests.post("https://api.sync.so/v2/generate", headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=30)
        else:
            # Local File Upload (Multipart)
            if not os.path.exists(audio_path):
                print(f"Audio file not found: {audio_path}")
                return "failed"
            
            # For Multipart, we send video as URL and audio as file
            # SyncLabs V2 Multipart expects 'video' and 'audio' fields
            files = {
                "audio": open(audio_path, "rb")
            }
            # Note: For V2 Multipart, 'model' and 'video' (if URL) are passed as data
            form_data = {
                "model": "lipsync-2",
                "video": base_video
            }
            r = requests.post("https://api.sync.so/v2/generate", headers=headers, data=form_data, files=files, timeout=45)
            files["audio"].close()

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
        r = requests.get(f"https://api.sync.so/v2/generate/{job_id}", headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {
            "status": data.get("status"),
            "video_url": data.get("videoUrl") if data.get("status") == "completed" else ""
        }
    except Exception as e:
        print(f"SyncLabs Polling Failed: {e}")
        return {"status": "failed"}

_last_checked_news = set()

@activity.defn
async def check_breaking_news_activity() -> list[dict]:
    global _last_checked_news
    try:
        from database import SessionLocal
        from models import News
        db = SessionLocal()
        latest = db.query(News).order_by(News.created_at.desc()).limit(10).all()
        db.close()
        
        breaking = []
        for n in latest:
            hid = str(n.id)
            if hid not in _last_checked_news:
                text = (n.headline + n.description).lower()
                if any(k in text for k in ["breaking", "urgent", "महत्त्वाची", "धक्कादायक", "मोठी बातमी"]):
                    breaking.append({"headline": n.headline, "description": n.description, "id": n.id})
                    _last_checked_news.add(hid)
        
        if len(_last_checked_news) > 100: _last_checked_news = set()
        return breaking
    except Exception as e:
        return []
