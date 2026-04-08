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
    anchor_gender = "महिला (Female)" if is_female else "पुरुष (Male)"
    gender_instruction = f"* व्याकरण (Grammar): अत्यंत शुद्ध आणि व्यावसायिक {language} भाषेचा वापर करा. कोणतीही व्याकरणीय चूक नको.\n* लिंग (Gender Rule): अँकर {anchor_gender} आहे. त्यामुळे स्वतःबद्दल बोलताना क्रियापदे '{anchor_gender}' लिंगानुसारच वापरा (उदा. पुरुष असल्यास 'मी सांगतो', 'माझा', महिला असल्यास 'मी सांगते', 'माझी'). हे अत्यंत महत्त्वाचे आहे!"

    system_prompt = f"""तुम्ही एक व्यावसायिक {language} वृत्तवाहिनीचे अँकर आहात. आता '{bulletin_name}' बुलेटिनची वेळ आहे.

नियम:
* भाषा पूर्णपणे शुद्ध आणि अधिकृत {language} असावी. वाक्यरचना अचूक आणि बातमीदाराला शोभेल अशी असावी.
* उच्चार स्पष्ट आणि प्रभावी असावेत
* बातमी सादरीकरणाचा वेग मध्यम असावा
* आवाजात आत्मविश्वास आणि गांभीर्य असावे
* सादरीकरण पुर्णपणे '{content_type}' या शैलीत असावे.
* केवळ बातमी (STRICT RULE): DO NOT add any greetings like "Namaskar", DO NOT introduce yourself or the channel, DO NOT add closing remarks, DO NOT add conversational fillers. YOU MUST START READING THE CORE SCRIPT DIRECTLY.
{gender_instruction}
"""
    user_prompt = f"""बातमी:
{news_data['headline']} - {news_data['description']}

कृपया वरील बातमीसाठी 'Varta Pravah - {bulletin_name}' या बुलेटिनची स्क्रिप्ट तयार करा. फक्त बातमीचा मजकूर द्या, दुसरे काहीही नाही:"""

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    script = completion.choices[0].message.content
    # Debug log removed to avoid Windows console UnicodeEncodeError
    
    # Placeholder for TTS (Google Cloud / ElevenLabs)
    audio_url = "https://example.com/audio.mp3"
    
    return {
        "script": script,
        "audio_url": audio_url,
        "is_female": is_female
    }

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
        "videoUrl": os.getenv("SYNC_LABS_BASE_VIDEO_URL"),
        "synergize": True
    }
    
    try:
        r = requests.post("https://api.synclabs.so/v2/lipsync", headers=headers, json=payload, timeout=5)
        r.raise_for_status()
        job_id = r.json().get("id")
        return job_id
    except Exception as e:
        print(f"SyncLabs currently unreachable or no credits: {e}. Falling back to dynamic mock generator.")
        
        script = data.get("script", "")
        if not script:
            return "mock_job_fallback"
            
        job_id = f"mock_job_fallback_{uuid.uuid4().hex}"
        out_audio = f"/app/{job_id}.mp3"
        out_video = f"/app/{job_id}.mp4"
        
        try:
            # 1. Generate Marathi Audio via Edge TTS
            # Wait, data dict doesn't natively carry is_female unless we pass it from generate_script_activity. 
            # In workflows.py, we passed is_female to generate_script_activity, but synclabs_lip_sync_activity receives the output of generate_script_activity.
            # We MUST extract is_female from data.
            is_female = data.get("is_female", False)
            voice = "mr-IN-AarohiNeural" if is_female else "mr-IN-ManoharNeural"
            subprocess.run(["python", "-m", "edge_tts", "--voice", voice, "--text", script, "--write-media", out_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            anchor_name = "anchor_female.mp4" if is_female else "anchor.mp4"
            anchor_mp4 = f"/app/{anchor_name}"
            
            # Sanitize the headline for FFmpeg (escape single quotes)
            headline_text = data.get("headline", "VARTA PRAVAH NEWS LIVE").replace("'", "\\'")
            
            # 2. Overlay anchor video over studio backdrop + generated audio + logo + professional news graphics
            # News display and tickers are drawn directly with drawtext filters
            # Ticker scrolling is achieved via 'mod(t*speed, text_w)' logic
            # 2. Overlay anchor video over studio backdrop + generated audio + logo + professional news graphics
            # News display and tickers are drawn directly with drawtext filters
            # We mix in music.mp3 at a low volume if it exists
            music_input = []
            audio_filter = "[3:a]volume=1.0[v];" # Default: only voice
            
            if os.path.exists("/app/music.mp3"):
                music_input = ["-i", "/app/music.mp3"]
                audio_filter = "[3:a]volume=1.2[v];[4:a]volume=0.1[m];[v][m]amix=inputs=2:duration=first[outa];"
            
            cmd = [
                "ffmpeg", "-y", 
                "-loop", "1", "-i", "/app/studio.jpg", # 0. Background
                "-stream_loop", "-1", "-i", anchor_mp4, # 1. Anchor
                "-i", "/app/logo.png", # 2. Logo
                "-i", out_audio # 3. Audio track (Voice)
            ] + music_input + [
                "-filter_complex", 
                # a) Scale background and core overlays to strict 720p (1280x720)
                "[0:v]scale=1280:720,setsar=1[bg];"
                "[1:v]colorkey=0x00FF00:0.3:0.2,scale=1280:720[anchor];"
                "[bg][anchor]overlay=(W-w)/2:(H-h)/2[base];"
                "[2:v]scale=180:-1[logoscale];"
                "[base][logoscale]overlay=W-w-140:40[withlogo];"
                # b) Draw News Ticker Bar (Bottom red bar)
                "[withlogo]drawbox=y=ih-110:w=iw:h=110:color=red@0.9:t=fill[tickerbg];"
                # c) Dynamic Headline (Stationary bold news title on the left)
                f"[tickerbg]drawtext=text='{headline_text}':fontcolor=white:fontsize=48:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:x=40:y=h-95:shadowcolor=black:shadowx=2:shadowy=2[withheadline];"
                # d) Scrolling Bottom Ticker (White sub-text moving right to left)
                "[withheadline]drawtext=text='VARTA PRAVAH NEWS - LIVE - FAST 100 - UPDATES EVERY 30 MINS - STAY TUNED':fontcolor=white:fontsize=32:x=w-mod(t*220,w+tw):y=h-40:shadowcolor=black:shadowx=2:shadowy=2[outv];" + 
                (audio_filter if music_input else "[3:a]volume=1.2[outa]"),
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
                "-shortest", 
                "-pix_fmt", "yuv420p", # Essential for streaming compatibility
                out_video
            ]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                print(f"ERROR: Local video generation failed! StdErr: {process.stderr}")
                raise Exception(f"FFmpeg generator failed with code {process.returncode}")
                
            if not os.path.exists(out_video) or os.path.getsize(out_video) < 1000:
                raise Exception("News segment file is missing or too small after generation.")
                
            return job_id
        except Exception as fallback_e:
            print(f"Failed to generate dynamic local video: {fallback_e}")
            return "mock_job_fallback"

@activity.defn
async def check_sync_labs_status_activity(job_id: str) -> dict:
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return {"status": "completed", "video_url": "https://example.com/mock_segment.mp4"}

    if job_id == "mock_job_fallback":
        return {"status": "completed", "video_url": os.getenv("SYNC_LABS_BASE_VIDEO_URL")}
        
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
        print(f"Error checking SyncLabs status: {e}. Defaulting to base video.")
        return {"status": "completed", "video_url": os.getenv("SYNC_LABS_BASE_VIDEO_URL")}

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

    # 1. Management: Cleanly annihilate any existing streamer for this channel
    playlist_name = f"playlist_{channel_id}.txt"
    try:
        print(f"Refreshing encoder for Channel {channel_id} to ensure 24/7 stability...")
        # Kill BOTH the bash while-true loop AND the child ffmpeg processes.
        subprocess.run(f"pkill -9 -f {playlist_name}", shell=True)
        # Give a small 2s buffer for ports/keys to clear
        time.sleep(2)
    except Exception as e:
        print(f"Check error (ignoring): {e}")

    # 2. Start fresh streamer (Initial start or Force Restart)
    try:
        streamer = Streamer(stream_key, channel_id)
        streamer.create_initial_playlist(video_url)
        streamer.start_stream()
        return "stream_started"
    except Exception as e:
        activity.logger.error(f"Failed to start stream: {e}")
        raise e

@activity.defn
async def stop_stream_activity(channel_id: int) -> str:
    playlist_name = f"playlist_{channel_id}.txt"
    try:
        print(f"Force stopping stream for channel {channel_id}")
        subprocess.run(f"pkill -9 -f {playlist_name}", shell=True)
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
