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
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return {
            "headline": "[MOCK] Regional Update",
            "description": "Mock description for testing the VartaPravah pipeline."
        }
    
    # 1. Fetch real news from World News API
    api_key = os.getenv("WORLD_NEWS_API_KEY")
    config = LANGUAGE_CONFIG.get(language, {"code": "hi", "region": "India"})
    region = config["region"]
    lang_code = config["code"]
    
    url = f"https://api.worldnewsapi.com/search-news?api-key={api_key}&text={region}&language={lang_code}&number=1"
    
    try:
        r = requests.get(url)
        data = r.json()
        if data.get("news"):
            news = data["news"][0]
            return {
                "headline": news["title"],
                "description": news["text"][:500]  # Limit text length
            }
    except Exception as e:
        print(f"Error fetching news: {e}")
    
    return {
        "headline": "Maharashtra Political Update",
        "description": "New developments in the state assembly regarding the budget."
    }

@activity.defn
async def generate_script_activity(input_data: dict) -> dict:
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

    system_prompt = f"""तुम्ही एक व्यावसायिक {language} वृत्तवाहिनीचे अँकर आहात. आता '{bulletin_name}' बुलेटिनची वेळ आहे.

नियम:
* भाषा पूर्णपणे शुद्ध आणि अधिकृत {language} असावी
* उच्चार स्पष्ट आणि प्रभावी असावेत
* बातमी सादरीकरणाचा वेग मध्यम असावा
* आवाजात आत्मविश्वास आणि गांभीर्य असावे
* सादरीकरण पुर्णपणे '{content_type}' या शैलीत असावे.
"""
    user_prompt = f"""बातमी:
{news_data['headline']} - {news_data['description']}

कृपया वरील बातमीसाठी 'Varta Pravah - {bulletin_name}' या बुलेटिनची स्क्रिप्ट तयार करा:"""

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
        "audio_url": audio_url
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
        out_audio = f"c:/VARTAPRAVAH/backend/{job_id}.mp3"
        out_video = f"c:/VARTAPRAVAH/backend/{job_id}.mp4"
        
        try:
            # 1. Generate Marathi Audio via gTTS
            tts = gTTS(text=script, lang='mr')
            tts.save(out_audio)
            
            # 2. Overlay anchor video over studio backdrop + generated audio
            cmd = [
                "ffmpeg", "-y", 
                "-i", "c:/VARTAPRAVAH/backend/anchor.mp4",
                "-loop", "1", "-i", "c:/VARTAPRAVAH/backend/studio.jpg",
                "-i", out_audio,
                "-filter_complex", "[0:v]scale=1280:720[anchor]; [1:v][anchor]overlay=(W-w)/2:(H-h)/2[outv]",
                "-map", "[outv]", "-map", "2:a",
                "-c:v", "libx264", "-c:a", "aac",
                "-shortest", out_video
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        return {"status": "completed", "video_url": f"c:/VARTAPRAVAH/backend/{job_id}.mp4"}

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
async def start_stream_activity(data: dict) -> str:
    channel_id = data["channel_id"]
    stream_key = data["stream_key"]
    video_url = data["video_url"]
    
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        print(f"[MOCK] Starting stream for channel {channel_id}")
        return "mock_stream_started"

    # 1. Check if FFmpeg is already running for this playlist
    # On Windows, we can check for the specific playlist filename in the command line
    playlist_name = f"playlist_{channel_id}.txt"
    try:
        # Check running processes with the playlist name
        # Tasklist /V gives the full command line window title usually, 
        # but a more robust way is WMIC or just trying to start and letting it fail/overwrite.
        # However, we'll try to be polite:
        res = subprocess.run(f'tasklist /FI "IMAGENAME eq ffmpeg.exe" /V', shell=True, capture_output=True, text=True)
        if playlist_name in res.stdout:
            print(f"Streamer already running for channel {channel_id}. Updating playlist.")
            streamer = Streamer(stream_key, channel_id)
            streamer.update_playlist(video_url)
            return "stream_updated"
    except Exception as e:
        print(f"Error checking processes: {e}")

    # 2. Start new streamer
    try:
        streamer = Streamer(stream_key, channel_id)
        streamer.create_initial_playlist(video_url)
        streamer.start_stream()
        return "stream_started"
    except Exception as e:
        activity.logger.error(f"Failed to start stream: {e}")
        raise e
