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
    
    # Surgical Cleanup
    try:
        if sys.platform == "win32":
            # On Windows, we try to find the specific FFmpeg process with the channel metadata
            # This is more complex than pkill, but necessary for multi-channel support on Windows
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    if proc.info['name'] == 'ffmpeg.exe':
                        cmdline = " ".join(proc.info['cmdline'])
                        if f"vp_channel={channel_id}" in cmdline:
                            print(f"Surgically killing FFmpeg PID {proc.info['pid']} for Channel {channel_id}")
                            proc.kill()
            except ImportError:
                # Fallback if psutil is not available (not recommended for multi-channel)
                print(f"WARNING: psutil not found. Falling back to generic taskkill for Channel {channel_id}")
                subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True)
        else:
            # Surgically kill only the FFmpeg process for this specific channel (Linux)
            subprocess.run(["pkill", "-9", "-f", f"vp_channel={channel_id}"], capture_output=True)
        print(f"Surgically cleaned up FFmpeg for channel {channel_id}")
    except Exception as e:
        print(f"Cleanup failed for channel {channel_id}: {e}")


@activity.defn
async def fetch_news_activity(language: str) -> list[dict]:
    load_dotenv(override=True)
    api_key = os.getenv("WORLD_NEWS_API_KEY")
    lang_code = LANGUAGE_CONFIG.get(language, {"code": "hi"})["code"]
    
    news_items = []
    priorities = [("Maharashtra", 4), ("India", 3), ("World", 3)]
    
    for category, count in priorities:
        url = f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text={category}&language={lang_code}&number={count}"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("news"):
                for n in data["news"]:
                    news_items.append({
                        "headline": n['title'],
                        "description": n['text'][:400],
                        "category": category
                    })
        except Exception as e:
            print(f"Error fetching {category} news: {e}")
            
    if not news_items:
        # Generic fallback if absolutely nothing found
        news_items = [{
            "headline": "Varta Pravah Breaking Updates",
            "description": "Namaskar, Maharashtra. Aaj chya thak batmya ani parinamkarak ghadamodi fakt Varta Pravah var.",
            "category": "BREAKING"
        }]
        
    return news_items[:10]


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
    audio_dir = os.path.join(BASE_DIR, "videos")
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, f"news_{uuid.uuid4().hex}.mp3")


    
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
    from models import Anchor
    db = SessionLocal()
    # Fetch the first active anchor matching the requested gender
    anchor = db.query(Anchor).filter(Anchor.gender == ("female" if is_female else "male"), Anchor.is_active == True).first()
    db.close()

    assets_dir = os.path.join(BASE_DIR, "assets")
    bg_p = os.path.join(assets_dir, "studio_bg.png")
    logo_p = os.path.join(assets_dir, "logo.png")
    
    # Use anchor portrait if found, else fallback to defaults
    if anchor and anchor.portrait_url:
        port_p = os.path.join(BASE_DIR, anchor.portrait_url)
    else:
        port_p = os.path.join(assets_dir, "female_anchor.png" if is_female else "male_anchor.png")

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

@activity.defn
async def ensure_promo_video_activity(channel_id: int = 1) -> bool:
    promo_p = os.path.join(BASE_DIR, "videos", f"promo_ch{channel_id}.mp4")
    master_promo = os.path.join(BASE_DIR, "videos", "promo.mp4")
    
    if not os.path.exists(promo_p) and os.path.exists(master_promo):
        import shutil
        shutil.copy2(master_promo, promo_p)
        print(f"Created channel-specific promo: {promo_p}")
        
    return os.path.exists(promo_p)

@activity.defn
async def start_stream_activity(data: dict) -> str:
    c_id, s_key, v_url = data["channel_id"], data["stream_key"], data["video_url"]
    _terminate_stream_process(c_id)
    time.sleep(2)
    try:
        if not os.path.isabs(v_url): v_url = os.path.join(BASE_DIR, v_url)
        # Fallback to channel-specific standby video
        fallback_v = os.path.join(BASE_DIR, "videos", f"promo_ch{c_id}.mp4")
        if not os.path.exists(v_url) or os.path.getsize(v_url) < 10000: 
            v_url = fallback_v if os.path.exists(fallback_v) else os.path.join(BASE_DIR, "videos", "promo.mp4")
            
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
async def ensure_premium_promo_activity() -> bool:
    output_path = os.path.join(BASE_DIR, "videos", "promo.mp4")
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000000:
        return True
    
    try:
        from create_premium_promo import create_premium_promo
        # Run in thread to avoid blocking worker
        await asyncio.to_thread(create_premium_promo, output_path)
        return os.path.exists(output_path)
    except Exception as e:
        print(f"Premium Promo Generation Error: {e}")
        return False

@activity.defn
async def get_video_duration_activity(file_path: str) -> float:
    if not os.path.exists(file_path): return 0.0
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return float(res.stdout.strip())
    except:
        return 0.0

@activity.defn
async def merge_videos_activity(video_paths: list[str]) -> str:

    if not video_paths: return ""
    if len(video_paths) == 1: return video_paths[0]
    
    # Filter out empty or missing paths
    valid_paths = [p for p in video_paths if p and os.path.exists(p)]
    if not valid_paths: return ""

    output_p = os.path.join(BASE_DIR, "videos", f"bulletin_{uuid.uuid4().hex}.mp4")
    
    # Create concat list
    list_p = os.path.join(tempfile.gettempdir(), f"concat_list_{uuid.uuid4().hex}.txt")
    with open(list_p, "w") as f:
        for p in valid_paths:
            # FFmpeg concat file expects escaped paths
            abs_p = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")
    
    try:
        # Use concat demuxer for fast, lossless stitching (assumes same resolution/codec)
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_p,
            "-c", "copy", output_p
        ], check=True)
        return output_p
    except Exception as e:
        print(f"Concat Error: {e}")
        return valid_paths[0]
    finally:
        try: os.remove(list_p)
        except: pass

@activity.defn
async def find_latest_bulletin_activity(channel_id: int) -> str:
    # Look for the most recent full bulletin for this channel
    video_dir = os.path.join(BASE_DIR, "videos")
    if not os.path.exists(video_dir): return ""
    
    files = [f for f in os.listdir(video_dir) if f.startswith(f"full_bulletin_ch{channel_id}_")]
    if not files:
        # Fallback to general bulletins if channel-specific not found (older format)
        files = [f for f in os.listdir(video_dir) if f.startswith("full_bulletin_")]
        
    if not files: return ""
    
    # Sort by modification time
    files.sort(key=lambda x: os.path.getmtime(os.path.join(video_dir, x)), reverse=True)
    return os.path.join(video_dir, files[0])

@activity.defn
async def stitch_bulletin_activity(data: dict) -> str:
    channel_id = data.get("channel_id", 0)
    # Organize news stories and promos into a 1-hour bulletin
    intro_path = data.get("intro_path")
    headlines_path = data.get("headlines_path")
    story_paths = data.get("story_paths", [])
    promo_path = data.get("promo_path")
    target_duration = 3600 # 1 hour
    
    if not story_paths: return ""
    
    final_sequence = []
    if intro_path and os.path.exists(intro_path):
        final_sequence.append(intro_path)
    if headlines_path and os.path.exists(headlines_path):
        final_sequence.append(headlines_path)
        
    block_news_count = 5 # ~5 minutes of news
    current_idx = 0
    
    # Assembly loop
    while True:
        # Add a block of stories
        for _ in range(block_news_count):
            if current_idx >= len(story_paths):
                # We ran out of stories, start repeating in shuffled order
                import random
                shuffled = story_paths[:]
                random.shuffle(shuffled)
                story_paths.extend(shuffled)
            
            final_sequence.append(story_paths[current_idx])
            current_idx += 1
            
        # Add Promo
        if promo_path and os.path.exists(promo_path):
            final_sequence.append(promo_path)
            
        # Check current duration
        if len(final_sequence) > 50: # Safety break (approx 50-60 mins)
            break

    # Final Merge
    video_dir = os.path.join(BASE_DIR, "videos")
    output_p = os.path.join(video_dir, f"full_bulletin_ch{channel_id}_{uuid.uuid4().hex}.mp4")


    list_p = os.path.join(tempfile.gettempdir(), f"stitch_list_{uuid.uuid4().hex}.txt")
    with open(list_p, "w") as f:
        for p in final_sequence:
            abs_p = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")
    
    try:
        # Step 1: Concat everything
        # On 4GB servers, we use a slower but safer re-encode for the first/last few frames
        # to ensure the file header is perfectly valid for YouTube.
        temp_p = os.path.join(tempfile.gettempdir(), f"full_merged_{uuid.uuid4().hex}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_p,
            "-c", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            temp_p
        ], check=True)
        
        # Step 2: Trim and Validate
        if not os.path.exists(temp_p) or os.path.getsize(temp_p) < 1000000: # 1MB minimum
             print("⚠️ Generated bulletin is too small/broken. Falling back.")
             return ""

        subprocess.run([
            "ffmpeg", "-y", "-t", "3600", "-i", temp_p,
            "-c", "copy", output_p
        ], check=True)

        
        try: os.remove(temp_p)
        except: pass
        
        return output_p
    except Exception as e:
        print(f"Stitch Error: {e}")
        return story_paths[0] if story_paths else ""
    finally:
        try: os.remove(list_p)
        except: pass

@activity.defn
async def get_channel_anchor_activity(channel_id: int) -> dict:
    return {"gender": "female", "name": "Priya"}


@activity.defn
async def upload_to_s3_activity(v_url: str) -> str: return v_url

@activity.defn
async def synclabs_lip_sync_activity(data: dict) -> str:
    """Sends audio and gender-appropriate base video to Sync Labs for lip-sync."""
    api_key = os.getenv("SYNCLABS_API_KEY")
    if not api_key: return "no_api_key"
    
    # --- PUBLIC URL CONVERSION ---
    # Sync Labs needs a public URL to download the audio.
    # We prioritize an environment variable SYNC_LABS_BASE_URL, then detect public IP.
    local_path = data.get("audio_url", "")
    filename = os.path.basename(local_path)
    
    base_url = os.getenv("SYNC_LABS_BASE_URL")
    if not base_url:
        public_ip = "localhost"
        for service in ["https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"]:
            try:
                public_ip = requests.get(service, timeout=5).text.strip()
                if public_ip: break
            except:
                continue
        base_url = f"http://{public_ip}:8000/videos"


    public_audio_url = f"{base_url}/{filename}"
    print(f"--- [SYNC LABS] Audio Source: {public_audio_url} ---")

    is_female = data.get("is_female", True)
    # Target high-quality base videos matching the anchor gender
    base_video = os.getenv("SYNC_LABS_FEMALE_VIDEO") if is_female else os.getenv("SYNC_LABS_MALE_VIDEO")
    
    if not base_video or "storage.googleapis.com" not in base_video:
        # Fallback to high-quality public assets if env vars aren't set or internal
        base_video = "https://storage.googleapis.com/varta-pravah/female_raw.mp4" if is_female else "https://storage.googleapis.com/varta-pravah/male_raw.mp4"


    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "audioUrl": public_audio_url, 
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
