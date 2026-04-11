import os
import requests
import json
import time
from temporalio import activity
from groq import Groq
from gtts import gTTS
import uuid
import subprocess
from dotenv import load_dotenv
import sys

# Import Streamer from parent directory (since worker is in temporal/)
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
    "Bengali": {"code": "bn", "region": "West Bengal"},
    "Telugu": {"code": "te", "region": "Telangana"},
    "Tamil": {"code": "ta", "region": "Tamil Nadu"},
    "Gujarati": {"code": "gu", "region": "Gujarat"},
    "Kannada": {"code": "kn", "region": "Karnataka"},
    "Malayalam": {"code": "ml", "region": "Kerala"},
    "Odia": {"code": "or", "region": "Odisha"},
    "Punjabi": {"code": "pa", "region": "Punjab"},
    "Assamese": {"code": "as", "region": "Assam"},
    "English": {"code": "en", "region": "India"},
}

STREAMER_INSTANCES: dict[int, Streamer] = {}

def _terminate_stream_process(channel_id: int):
    streamer = STREAMER_INSTANCES.pop(channel_id, None)
    if not streamer:
        return
    try:
        streamer.stop_stream()
    except Exception as e:
        print(f"Error terminating existing streamer for channel {channel_id}: {e}")

@activity.defn
async def fetch_news_activity(language: str) -> dict:
    load_dotenv(override=True)
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return {
            "headline": "[MOCK] Regional Update",
            "description": "Mock description for testing the VartaPravah pipeline."
        }
    
    # 1. Fetch real news from World News API prioritizing Maharashtra, National, and World
    api_key = os.getenv("WORLD_NEWS_API_KEY")
    lang_code = LANGUAGE_CONFIG.get(language, {"code": "hi", "region": "India"})["code"]
    
    combined_headline = "Top Updates: "
    combined_description = ""
    
    # Define priorities (Stronger Marathi Keywords)
    priorities = [
        ("Maharashtra OR महाराष्ट्र", 3), 
        ("India OR भारत", 3), 
        ("World OR जागतिक", 2)
    ]
    
    for category, count in priorities:
        url = f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text={category}&language={lang_code}&number={count}"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("news"):
                for n in data["news"]:
                    combined_headline += f" | {n['title']}"
                    combined_description += f"\n[{category.upper()} NEWS]: {n['text'][:250]}..."
        except Exception as e:
            print(f"Error fetching {category} news: {e}")
            
    if not combined_description:
        # Emergency News Fallback: High-Quality Curated Local News
        print("Using Curated Fallback News Sequence...")
        combined_headline += " | महाराष्ट्रातील महत्त्वाच्या बातम्या | भारताचे प्रगतीपथावरील पाऊल"
        combined_description = """
        [MAHARASHTRA NEWS]: महाराष्ट्रातील आजच्या महत्त्वाच्या घडामोडी आणि राजकीय वातावरणाचा आढावा.
        [INDIA NEWS]: भारताची जागतिक स्तरावरील आर्थिक प्रगती आणि तंत्रज्ञान क्षेत्रातील प्रगतीचा आढावा.
        [WORLD NEWS]: जागतिक स्तरावर घडणाऱ्या घडामोडींचे आजचे सविस्तर वार्तापत्र.
        """
    
    return {
        "headline": combined_headline,
        "description": combined_description
    }

@activity.defn
async def get_channel_anchor_activity(channel_id: int) -> dict:
    """Fetch the preferred anchor for a channel."""
    try:
        db = database.SessionLocal()
        channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
        db.close()
        
        if not channel or not channel.preferred_anchor_id:
            # Default to male if no anchor is set
            return {"gender": "male", "anchor_id": None, "name": "Default"}
        
        db = database.SessionLocal()
        anchor = db.query(models.Anchor).filter(models.Anchor.id == channel.preferred_anchor_id).first()
        db.close()
        
        if anchor:
            return {"gender": anchor.gender, "anchor_id": anchor.id, "name": anchor.name}
        else:
            return {"gender": "male", "anchor_id": None, "name": "Default"}
    except Exception as e:
        print(f"Error fetching anchor for channel {channel_id}: {e}")
        return {"gender": "male", "anchor_id": None, "name": "Default"}

@activity.defn
async def generate_script_activity(input_data: dict) -> dict:
    load_dotenv(override=True)
    news_data = input_data["news_data"]
    language = input_data["language"]
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return {
            "script": "[MOCK] Marathi News Script...",
            "audio_url": "https://example.com/mock_audio.mp3"
        }

    from datetime import datetime, timezone, timedelta
    
    # Get current IST Time
    ist = timezone(timedelta(hours=5, minutes=30))
    current_time = datetime.now(ist)
    hour = current_time.hour
    
    # Apply TV-Standard Schedule Rules
    if 6 <= hour < 12:
        bulletin_name = "सकाळ"
        content_type = "Top headlines and morning updates"
    elif 12 <= hour < 18:
        bulletin_name = "दुपार"
        content_type = "Updates and breaking news"
    elif 18 <= hour < 21:
        bulletin_name = "संध्याकाळ"
        content_type = "Detailed reporting"
    elif 21 <= hour < 23:
        bulletin_name = "प्राइम टाइम"
        content_type = "Deep analysis and critical insights"
    else: # 23:00 to 05:59
        bulletin_name = "रात्री"
        content_type = "Summary of the day's major events"

    is_female = input_data.get("is_female", False)
    anchor_gender = "महिला" if is_female else "पुरुष"
    gender_instruction = f"* अँकर {anchor_gender} आहे. स्वतःविषयी बोलताना मराठी व्याकरणानुसार योग्य क्रियापदे वापरा (उदा. पुरुष असल्यास 'मी सांगतो', महिला असल्यास 'मी सांगते')."

    system_prompt = f"""तुम्ही एक अभिज्ञ व्यावसायिक मराठी समाचार अँकर आहात ज्यांचा समाचार प्रसारणामध्ये 10 वर्षांचा अनुभव आहे.

तुमचे मुख्य उद्देश्य:
1. समाचार स्पष्ट, पूर्ण आणि तार्किक पद्धतीने सादर करणे
2. प्रत्येक घटनेचा संपूर्ण संदर्भ समजावून सांगणे
3. श्रोत्यांना संपूर्ण माहिती देणे

तुमची भाषा नियमावली:
* फक्त शुद्ध, व्याकरणदृष्ट्या अचूक मराठी वापरा. कोणतेही इंग्रजी किंवा हिंदी शब्द नका.
* सरल पण व्यावसायिक शब्दावली वापरा
* लांब परंतु सहज समजणाऱ्या वाक्यांचा उपयोग करा
* प्रत्येक तपशिल स्पष्ट आणि अचूकरित्या समजावून सांगा
* दुरुस्त शब्द चयन आणि उच्चारण शैलीचा कठोर पालन करा

स्क्रिप्ट संरचना:
1. मुख्य बातमी - संपूर्ण, अर्थपूर्ण आणि तार्किक हेडलाइन
2. विस्तृत विवरण - प्रत्येक महत्वाचा बिंदू वेगळ्या पाराग्राफमध्ये
3. पार्श्वभूमी - संदर्भ, तारीख, स्थाने, व्यक्तींची माहिती
4. परिणाम - घटनेचे संभावित परिणाम आणि प्रभाव

महत्वाचे नियम:
* शुरुवात आणि अंतचे अभिवादन टाळा
* केवळ बातमीचा मजकूर द्या
* तर्कसंगत आणि तार्किक क्रमानुसार सामग्री व्यवस्थित करा
* प्रत्येक वाक्य पूर्ण आणि स्वतंत्र असावा
* भावनिक किंवा पूर्वाग्रही भाषा टाळा

{gender_instruction}

तुम्ही समाचार सादर करत आहात {bulletin_name} या वेळी, ज्यात {content_type} दिली जातात."""
    user_prompt = f"""तुम्हाला खालील बातमीच्या आधारावर व्यावसायिक, अधिकृत मराठी वृत्त स्क्रिप्ट तयार करायची आहे.

बातमी:
{news_data['headline']} 
विस्तार: {news_data['description']}

स्क्रिप्ट संरचना:
१. मुख्य बातमी (खोल हेडलाइन): एक पूर्ण, सविस्तर आणि अर्थपूर्ण मुख्य वाक्य जो संपूर्ण घटनेचा सारांश देते.
२. महत्वाचे तपशील: प्रत्येक महत्वाचा मुद्दा विस्तारपूर्वक समजावून सांगा (कारण, परिणाम, संदर्भ).
३. अतिरिक्त संदर्भ: संबंधित पार्श्वभूमी माहिती, तारीख, स्थाने, व्यक्तींची नावे आणि प्रभाव.

आवश्यक गोष्टी:
* मुख्य हेडलाइन 15-25 शब्दांची असावी आणि संपूर्ण घटना स्पष्ट करावी
* प्रत्येक तपशिल 2-3 संपूर्ण वाक्यांमध्ये उचल अशा प्रकारे समजावून सांगा
* कमीत कमी 4-5 मुख्य मुद्दे समाविष्ट करा
* तर्कसंगत क्रमाने मुद्दे व्यवस्थित करा (महत्वाचे ते कमी महत्वाचे)
* पूर्ण, सार्थक वाक्य वापरा
* कोणतेही स्वागत, अभिवादन किंवा समारोप टाळा
* सर्व मजकूर शुद्ध मराठीमध्ये असावा

'Varta Pravah - {bulletin_name}' या बुलेटिनसाठी स्क्रिप्ट तयार करा."""

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    script = completion.choices[0].message.content
    # Debug log removed to avoid Windows console UnicodeEncodeError
    
    return {
        "script": script,
        "is_female": is_female
    }

@activity.defn
async def generate_audio_activity(input_data: dict) -> str:
    """Generate TTS audio locally from the script."""
    import subprocess
    import tempfile

    try:
        script = input_data.get("script", "")
        language = input_data.get("language", "Marathi")
        lang_code = LANGUAGE_CONFIG.get(language, {"code": "mr"})["code"]

        os.makedirs("/tmp", exist_ok=True)
        audio_path = os.path.join("/tmp", f"news_audio_{uuid.uuid4().hex}.mp3")
        
        try:
            tts = gTTS(text=script or "Breaking news update.", lang=lang_code)
            tts.save(audio_path)
            if os.path.exists(audio_path):
                print(f"Generated TTS audio: {audio_path}")
                return audio_path
        except Exception as e:
            print(f"Error generating TTS audio: {e}. Falling back to silent audio.")

        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", "10", "-c:a", "libmp3lame", audio_path
        ], capture_output=True, check=False)
        if os.path.exists(audio_path):
            return audio_path
        raise RuntimeError("Failed to create fallback silent audio")
    except Exception as e:
        print(f"generate_audio_activity failed: {e}")
        return "/app/videos/promo.mp4"

@activity.defn
async def generate_news_video_activity(input_data: dict) -> str:
    """Generate professional news studio video like real news channels."""
    import subprocess
    from PIL import Image, ImageDraw, ImageFont
    import textwrap
    
    try:
        news_title = input_data.get("title", "Breaking News")
        audio_url = input_data.get("audio_url", "")
        
        output_path = "/app/videos/news_generated.mp4"
        os.makedirs("/app/videos", exist_ok=True)
        tmp_dir = "/tmp/news_video"
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Create professional news studio background
        width, height = 1920, 1080
        
        # Create gradient background (dark to lighter gradient like professional news channels)
        studio_img = Image.new('RGB', (width, height), color=(15, 25, 45))
        draw = ImageDraw.Draw(studio_img)
        
        # Draw gradient background (dark navy to dark blue)
        for y in range(height):
            # Create gradient from top (15,25,45) to bottom (30,50,80)
            ratio = y / height
            r = int(15 + (30 - 15) * ratio)
            g = int(25 + (50 - 25) * ratio)
            b = int(45 + (80 - 45) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add accent bar (blue/cyan line) at top
        accent_height = 8
        draw.rectangle([(0, 0), (width, accent_height)], fill=(0, 180, 255))
        
        # Add background graphics elements
        # Left side accent bar
        draw.rectangle([(0, accent_height), (12, height)], fill=(0, 180, 255))
        
        # Professional news ticker background at bottom
        ticker_height = 100
        draw.rectangle([(0, height - ticker_height), (width, height)], fill=(20, 35, 60))
        
        # Separator line above ticker
        draw.line([(0, height - ticker_height), (width, height - ticker_height)], fill=(0, 180, 255), width=3)
        
        # Load fonts
        try:
            title_font_size = 90
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", title_font_size)
        except Exception:
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
            except Exception:
                title_font = ImageFont.load_default()
        
        try:
            ticker_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except Exception:
            ticker_font = ImageFont.load_default()
        
        # Main headline - wrap and center
        max_width = 45  # characters per line
        wrapped_lines = textwrap.wrap(news_title, width=max_width)
        
        # Calculate headline area position and size
        headline_start_y = 150
        line_spacing = 110
        
        # Draw main headline
        for i, line in enumerate(wrapped_lines):
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Position from left with padding
            x_position = 100
            y_position = headline_start_y + (i * line_spacing)
            
            # Draw white text with shadow effect
            shadow_offset = 4
            draw.text((x_position + shadow_offset, y_position + shadow_offset), line, font=title_font, fill=(0, 0, 0, 70))
            draw.text((x_position, y_position), line, font=title_font, fill=(255, 255, 255))
        
        # Add "LIVE" indicator if breaking news
        if "Breaking" in news_title or "तातडीचे" in news_title:
            live_x = 1700
            live_y = 50
            draw.ellipse([(live_x, live_y), (live_x + 40, live_y + 40)], fill=(255, 50, 50))
            try:
                live_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            except:
                live_font = ImageFont.load_default()
            draw.text((live_x + 50, live_y + 5), "LIVE", font=live_font, fill=(255, 50, 50))
        
        # Add logo/channel name in top right corner
        try:
            logo_font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", 36)
        except:
            try:
                logo_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            except:
                logo_font = ImageFont.load_default()
        
        channel_text = "वार्ता प्रवाह"
        text_bbox = draw.textbbox((0, 0), channel_text, font=logo_font)
        text_width = text_bbox[2] - text_bbox[0]
        logo_x = width - text_width - 50
        logo_y = 30
        draw.text((logo_x, logo_y), channel_text, font=logo_font, fill=(0, 180, 255))
        
        # Add news ticker text at bottom
        ticker_text = "आज की मुख्य बातमियां | वार्ता प्रवाह - आपका विश्वसनीय समाचार स्रोत"
        ticker_x = 30
        ticker_y = height - ticker_height + 25
        draw.text((ticker_x, ticker_y), ticker_text, font=ticker_font, fill=(200, 200, 200))
        
        # Add time display in bottom right
        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        current_time = datetime.now(ist).strftime("%H:%M")
        time_bbox = draw.textbbox((0, 0), current_time, font=ticker_font)
        time_width = time_bbox[2] - time_bbox[0]
        draw.text((width - time_width - 30, ticker_y), current_time, font=ticker_font, fill=(100, 200, 255))
        
        # Save the professional studio frame
        headline_img_path = os.path.join(tmp_dir, "news_studio_frame.jpg")
        studio_img.save(headline_img_path, quality=95)
        
        # Resolve audio source
        audio_path = audio_url
        if audio_path and os.path.isfile(audio_path):
            print(f"Using existing audio file: {audio_path}")
        elif audio_path and audio_path.startswith("http"):
            audio_downloaded = os.path.join(tmp_dir, "news_audio_downloaded.mp3")
            try:
                import urllib.request
                urllib.request.urlretrieve(audio_path, audio_downloaded)
                audio_path = audio_downloaded
            except Exception as e:
                print(f"Failed to download audio URL {audio_path}: {e}")
                audio_path = ""
        
        if not audio_path or not os.path.isfile(audio_path):
            audio_path = os.path.join(tmp_dir, "news_audio_fallback.mp3")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-t", "10", "-c:a", "libmp3lame", audio_path
            ], capture_output=True, check=False)

        if not os.path.isfile(audio_path):
            raise RuntimeError(f"Audio path missing after fallback creation: {audio_path}")

        # Create video from professional studio frame + audio using FFmpeg
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", headline_img_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            "-t", "10",
            output_path
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"Successfully generated professional news video: {output_path}")
            return output_path
        else:
            print(f"FFmpeg error generating news video: {result.stderr}")
            return "/app/videos/promo.mp4"
            
    except Exception as e:
        print(f"Error generating news video locally: {e}. Falling back to promo.")
        return "/app/videos/promo.mp4"

@activity.defn
async def synclabs_lip_sync_activity(data: dict) -> str:
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return "mock_job_123"

    # 1. Call Sync Labs Real API
    headers = {
        "x-api-key": os.getenv("SYNCLABS_API_KEY"),
        "Content-Type": "application/json"
    }
    payload = {
        "audioUrl": data['audio_url'], 
        "videoUrl": os.getenv("SYNC_LABS_BASE_VIDEO_URL", "/app/videos/promo.mp4"),
        "synergize": True
    }
    
    try:
        r = requests.post("https://api.synclabs.so/v2/lipsync", headers=headers, json=payload, timeout=5)
        r.raise_for_status()
        job_id = r.json().get("id")
        return job_id
    except Exception as e:
        print(f"SyncLabs currently unreachable or no credits: {e}. Falling back to promo stream.")
        return "mock_job_fallback_promo"

@activity.defn
async def check_sync_labs_status_activity(job_id: str) -> dict:
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        if job_id == "mock_job_123":
            return {"status": "completed", "video_url": "/app/videos/news_ready.mp4"}
        return {"status": "completed", "video_url": "https://example.com/mock_segment.mp4"}

    if job_id == "mock_job_fallback":
        return {"status": "completed", "video_url": os.getenv("SYNC_LABS_BASE_VIDEO_URL")}
        
    if job_id == "mock_job_fallback_promo":
        return {"status": "completed", "video_url": "/app/videos/promo.mp4"}
        
    if job_id.startswith("mock_job_fallback_"):
        return {"status": "completed", "video_url": f"/app/{job_id}.mp4"}

    # 1. Poll Sync Labs Real API
    headers = {"x-api-key": os.getenv("SYNCLABS_API_KEY")}
    try:
        r = requests.get(f"https://api.synclabs.so/v2/lipsync/{job_id}", headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        return {
            "status": data.get("status"),
            "video_url": data.get("videoUrl") if data.get("status") == "completed" else ""
        }
    except Exception as e:
        print(f"Error checking SyncLabs status: {e}. Defaulting to promo video.")
        return {"status": "completed", "video_url": "/app/videos/promo.mp4"}

@activity.defn
async def upload_to_s3_activity(video_url: str) -> str:
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return "s3://mock-bucket/mock_news_segment.mp4"

    # 1. Download from Sync Labs URL
    # 2. Upload to User S3 (Placeholder for production)
    print(f"Syncing {video_url} to streaming engine...")
    return video_url  # For now return the URL directly for the streamer

@activity.defn
async def ensure_promo_video_activity() -> bool:
    promo_path = "/app/videos/promo.mp4"
    sentinel_path = "/app/videos/.promo_studio_ok"
    image_path = "/app/studio.jpg"
    os.makedirs("/app/videos", exist_ok=True)

    # ── Quick Return: If promo exists, use it immediately to start stream ──
    if os.path.exists(promo_path):
        print(f"✅ Promo asset found ({os.path.getsize(promo_path)//1024} KB) — playing immediately")
        return True

    print("🎬 Generating 60-second promo video (first-time setup)…")

    # Common encoder flags — MUST match streamer.py exactly
    encode_flags = [
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-r", "30",
        "-g", "60",
        "-keyint_min", "60",
        "-x264opts", "scenecut=0",   # safer than deprecated -sc_threshold
        "-pix_fmt", "yuv420p",
        "-b:v", "1000k",
        "-c:a", "aac",
        "-ar", "44100",
        "-b:a", "128k",
        promo_path,
    ]

    # ── Attempt 1: Gen-Z animated neon promo ──────────────────────────────
    try:
        print("🎨 Generating Gen-Z neon promo via create_genz_promo…")
        import importlib.util as _ilu
        _script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "create_genz_promo.py")
        _spec = _ilu.spec_from_file_location("create_genz_promo", _script)
        _mod  = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        ok = _mod.create_genz_promo(promo_path)
        if ok and os.path.exists(promo_path):
            print(f"✅ Gen-Z promo ready ({os.path.getsize(promo_path)//1024} KB)")
            open(sentinel_path, "w").close()
            return True
        print("⚠️  Gen-Z promo script returned failure — falling through")
    except Exception as e:
        print(f"⚠️  Gen-Z promo attempt exception: {e}")

    # ── Attempt 2: Use studio.jpg if available ─────────────────────────────
    if os.path.exists(image_path):
        try:
            cmd = [
                "ffmpeg", "-y", "-loglevel", "warning",
                "-loop", "1", "-i", image_path,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", "60",
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                       "pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-map", "0:v", "-map", "1:a",
            ] + encode_flags
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if result.returncode == 0 and os.path.exists(promo_path):
                print(f"✅ Promo from studio.jpg ({os.path.getsize(promo_path)//1024} KB)")
                # Write sentinel so next startup skips regeneration
                open(sentinel_path, "w").close()
                return True
            print(f"⚠️  studio.jpg attempt failed: {result.stderr[-300:]}")
        except Exception as e:
            print(f"⚠️  studio.jpg attempt exception: {e}")

    # ── Attempt 3: Ultra-minimal — plain black frame, guaranteed to work ──
    try:
        print("🎬 Generating minimal black-frame promo (last resort)…")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "warning",
            "-f", "lavfi", "-i", "color=black:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", "60",
            "-map", "0:v", "-map", "1:a",
        ] + encode_flags
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and os.path.exists(promo_path):
            print(f"✅ Minimal promo created ({os.path.getsize(promo_path)//1024} KB)")
            return True
        print(f"❌ Even minimal promo failed: {result.stderr[-300:]}")
    except Exception as e:
        print(f"❌ Minimal promo exception: {e}")

    return False




@activity.defn
async def start_stream_activity(data: dict) -> str:
    channel_id = data["channel_id"]
    stream_key = data["stream_key"]
    video_url = data["video_url"]
    is_promo = data.get("is_promo", False)
    
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        print(f"[MOCK] Starting stream for channel {channel_id}")
        return "mock_stream_started"

    # 1. Management: Cleanly terminate any existing streamer for this channel
    _terminate_stream_process(channel_id)
    time.sleep(2)

    # 2. Start fresh streamer (Initial start or Force Restart)
    try:
        if video_url.startswith("/app/") and not os.path.exists(video_url):
            print(f"Video path {video_url} is missing. Falling back to promo video.")
            video_url = "/app/videos/promo.mp4"

        if not stream_key or len(stream_key) < 5:
            activity.logger.error(f"Invalid stream key for channel {channel_id}")
            return "failed_invalid_key"

        streamer = Streamer(stream_key, channel_id)
        streamer.create_initial_playlist(video_url)
        streamer.start_stream()
        
        # Store the whole instance so we can stop the monitor thread later
        STREAMER_INSTANCES[channel_id] = streamer
        return "stream_started"
    except Exception as e:
        activity.logger.error(f"Failed to start stream: {e}")
        raise e

@activity.defn
async def stop_stream_activity(channel_id: int) -> str:
    try:
        print(f"Force stopping stream for channel {channel_id}")
        _terminate_stream_process(channel_id)
        return "stream_stopped"
    except Exception as e:
        print(f"Error stopping stream: {e}")
        return "error"

@activity.defn
async def check_scheduled_ads_activity(data: dict) -> list[str]:
    channel_id = data["channel_id"]
    hour = data["hour"] # e.g. "08", "14", etc.
    
    from database import SessionLocal
    from models import AdCampaign
    
    db = SessionLocal()
    try:
        # Search for ads where the scheduled hours string contains this hour
        # e.g. "08:00,12:00" contains "08"
        ads = db.query(AdCampaign).filter(
            AdCampaign.channel_id == channel_id,
            AdCampaign.is_active == True,
            AdCampaign.scheduled_hours.contains(hour)
        ).all()
        
        return [ad.video_url for ad in ads]
    except Exception as e:
        print(f"Error checking ads: {e}")
        return []
    finally:
        db.close()

@activity.defn
async def cleanup_old_videos_activity() -> str:
    """Auto-delete videos older than 24 hours to save space."""
    video_dir = "/app"
    if not os.path.exists(video_dir):
        return "Directory missing"
        
    now = time.time()
    deleted_count = 0
    for f in os.listdir(video_dir):
        file_path = os.path.join(video_dir, f)
        if os.path.getmtime(file_path) < now - (24 * 3600):
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception:
                pass
    return f"Cleanup complete: Deleted {deleted_count} files."
