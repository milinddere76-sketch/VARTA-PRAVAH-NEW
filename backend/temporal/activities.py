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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streamer import Streamer

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

STREAM_PROCESSES: dict[int, subprocess.Popen] = {}

def _terminate_stream_process(channel_id: int):
    process = STREAM_PROCESSES.pop(channel_id, None)
    if not process:
        return
    try:
        process.terminate()
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
    except Exception as e:
        print(f"Error terminating existing stream process for channel {channel_id}: {e}")

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

    system_prompt = f"""तुम्ही एक व्यावसायिक मराठी वृत्तवाहिनीचे मुख्य अँकर आहात.

तुमची भाषा पूर्णपणे शुद्ध, अधिकृत आणि वृत्तात्मक असावी.

नियम:
* फक्त मराठीच वापरा. इंग्रजी शब्दांचा किंवा ट्रान्सलिटरेशनचा वापर करू नका.
* व्याकरण पूर्णपणे बरोबर असावे.
* शिस्तबद्ध, तथ्यात्मक आणि ताणलेले आशय द्या.
* परिचय, अभिवादन, समारोप किंवा वैयक्तिक टिप्पणी वापरू नका.
* प्रसारमाध्यमीय वृत्तनिबंध शैलीत लिहा.
* प्रत्येक वाक्य स्पष्ट आणि अचूक असावे.
* कोणतीही गोंधळ किंवा शिथिलता असू नये.
{gender_instruction}
"""
    user_prompt = f"""तुम्हाला खालील बातमीच्या मुख्य मुद्द्यांवर आधारीत व्यावसायिक, अधिकृत आणि व्याकरणदृष्ट्या अचूक मराठी वृत्त स्क्रिप्ट तयार करायची आहे.

बातमी:
{news_data['headline']} - {news_data['description']}

* फक्त महत्वाचे मुद्दे समाविष्ट करा.
* कमीतकमी 3-4 वाक्यांचा प्रवाही रिपोर्ट द्या.
* कोणतेही स्वागत/परिचय/समारोप टाळा.
* मजकूर पूर्णपणे मराठी असावा.

'Varta Pravah - {bulletin_name}' या बुलेटिनसाठी स्क्रिप्ट तयार करा."""

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=1024,
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
    """Generate simple news video locally without SyncLabs lip-sync capability."""
    import subprocess
    from PIL import Image, ImageDraw, ImageFont
    import textwrap
    
    try:
        news_title = input_data.get("title", "Breaking News")
        audio_url = input_data.get("audio_url", "")
        
        output_path = "/app/videos/news_generated.mp4"
        os.makedirs("/app/videos", exist_ok=True)
        
        # Create news headline image overlay
        studio_img = Image.open("/app/studio.jpg")
        draw = ImageDraw.Draw(studio_img)
        
        # Try to use a Devanagari-capable font, fallback to DejaVu if not available
        try:
            font_size = 70
            font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
        
        # Wrap text to fit the image width
        max_width = 60  # characters per line
        wrapped_lines = textwrap.wrap(news_title, width=max_width)
        
        # Draw headline text in center with white color and black outline
        y_position = 250
        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x_position = (1280 - text_width) // 2
            
            # Draw black outline
            for adj_x in [-2, -1, 0, 1, 2]:
                for adj_y in [-2, -1, 0, 1, 2]:
                    draw.text((x_position + adj_x, y_position + adj_y), line, font=font, fill="black")
            
            # Draw white text
            draw.text((x_position, y_position), line, font=font, fill="white")
            y_position += text_height + 20
        
        # Save headline image
        tmp_dir = "/tmp/news_video"
        os.makedirs(tmp_dir, exist_ok=True)
        headline_img_path = os.path.join(tmp_dir, "news_headline.jpg")
        studio_img.save(headline_img_path)
        
        # Resolve audio source
        audio_path = input_data.get("audio_url", "")
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

        # Create video from image + audio using FFmpeg
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
            print(f"Successfully generated news video: {output_path}")
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
    image_path = "/app/studio.jpg"
    
    # Ensure videos directory exists
    os.makedirs("/app/videos", exist_ok=True)
    
    # If we need to upgrade the promo (e.g. to add audio), we delete it here once
    # For now, let's just make it robust.
    
    if os.path.exists(promo_path) and os.path.getsize(promo_path) > 1000:
        return True
    
    if not os.path.exists(image_path):
        print(f"Fallback image {image_path} missing. Cannot generate promo.")
        return False
        
    print(f"Generating professional promo video with audio from {image_path}...")
    try:
        logo_path = None
        for candidate in ["/app/logo.png", "/app/logo.svg"]:
            if os.path.exists(candidate):
                logo_path = candidate
                break

        if logo_path:
            cmd = [
                "ffmpeg", "-y", 
                "-loop", "1", "-i", image_path,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-i", logo_path,
                "-t", "15",
                "-filter_complex", "[0:v]scale=1280:720,format=yuv420p[bg];[bg][2:v]overlay=W-w-20:20:format=auto",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", "-b:a", "128k", "-shortest",
                promo_path
            ]
        else:
            cmd = [
                "ffmpeg", "-y", 
                "-loop", "1", "-i", image_path,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", "15",
                "-vf", "scale=1280:720,format=yuv420p",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", "-b:a", "128k", "-shortest",
                promo_path
            ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Failed to generate promo video: {e}")
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

        streamer = Streamer(stream_key, channel_id)
        streamer.create_initial_playlist(video_url)
        streamer.start_stream()
        STREAM_PROCESSES[channel_id] = streamer.process
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
