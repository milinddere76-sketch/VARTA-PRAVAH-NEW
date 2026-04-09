import os
import requests
import time
from temporalio import activity
from groq import Groq
from gtts import gTTS
import uuid
import subprocess
from dotenv import load_dotenv
import sys
from typing import Dict

# Import Streamer safely
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streamer import Streamer

# Load env
load_dotenv()

LANGUAGE_CONFIG = {
    "Marathi": {"code": "mr", "region": "Maharashtra"},
    "Hindi": {"code": "hi", "region": "India"},
    "English": {"code": "en", "region": "India"},
}

# Safe process tracker
STREAM_PROCESSES: Dict[int, subprocess.Popen] = {}


# ================= PROCESS MANAGEMENT ================= #

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
        print(f"Error terminating stream {channel_id}: {e}")


# ================= SAFE REQUEST ================= #

def safe_request(url):
    try:
        return requests.get(url, timeout=5)
    except Exception:
        return None


# ================= FETCH NEWS ================= #

@activity.defn
async def fetch_news_activity(language: str) -> dict:
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return {
            "headline": "[MOCK] News",
            "description": "Mock news description"
        }

    api_key = os.getenv("WORLD_NEWS_API_KEY")
    lang_code = LANGUAGE_CONFIG.get(language, {"code": "hi"})["code"]

    url = f"https://api.worldnewsapi.com/search-news?api-key={api_key}&language={lang_code}&number=5"
    r = safe_request(url)

    if r and r.status_code == 200:
        data = r.json()
        news = data.get("news", [])
        if news:
            return {
                "headline": news[0]["title"],
                "description": news[0]["text"][:300]
            }

    return {
        "headline": "Breaking News",
        "description": "Important updates will follow shortly."
    }


# ================= SCRIPT ================= #

@activity.defn
async def generate_script_activity(input_data: dict) -> dict:
    if os.getenv("MOCK_MODE", "false").lower() == "true":
        return {"script": "Mock script"}

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    for _ in range(3):
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": input_data["news_data"]["headline"]}],
            )
            return {"script": completion.choices[0].message.content}
        except Exception:
            time.sleep(2)

    return {"script": "Breaking news update."}


# ================= AUDIO ================= #

@activity.defn
async def generate_audio_activity(input_data: dict) -> str:
    try:
        script = input_data.get("script", "")
        path = f"/tmp/audio_{uuid.uuid4().hex}.mp3"

        tts = gTTS(text=script, lang="mr")
        tts.save(path)

        if os.path.exists(path):
            return path

    except Exception as e:
        print(f"TTS error: {e}")

    # fallback silent audio
    fallback = "/tmp/silent.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-t", "5", fallback
    ], timeout=20)

    return fallback


# ================= VIDEO ================= #

@activity.defn
async def generate_news_video_activity(input_data: dict) -> str:
    output = "/app/videos/news.mp4"
    os.makedirs("/app/videos", exist_ok=True)

    if not os.path.exists("/app/studio.jpg"):
        return "/app/videos/promo.mp4"

    try:
        subprocess.run([
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", "/app/studio.jpg",
            "-f", "lavfi",
            "-i", "anullsrc",
            "-t", "10",
            "-c:v", "libx264",
            "-c:a", "aac",
            output
        ], timeout=30)

        return output

    except Exception as e:
        print(f"Video error: {e}")
        return "/app/videos/promo.mp4"


# ================= STREAM ================= #

@activity.defn
async def start_stream_activity(data: dict) -> str:
    channel_id = data["channel_id"]

    _terminate_stream_process(channel_id)

    try:
        video = data["video_url"]
        if not os.path.exists(video):
            video = "/app/videos/promo.mp4"

        streamer = Streamer(data["stream_key"], channel_id)
        streamer.create_initial_playlist(video)
        streamer.start_stream()

        if streamer.process:
            STREAM_PROCESSES[channel_id] = streamer.process

        return "started"

    except Exception as e:
        activity.logger.error(str(e))
        return "error"


@activity.defn
async def stop_stream_activity(channel_id: int) -> str:
    _terminate_stream_process(channel_id)
    return "stopped"


# ================= ADS ================= #

@activity.defn
async def check_scheduled_ads_activity(data: dict) -> list:
    from database import get_session_local
    from models import AdCampaign

    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        ads = db.query(AdCampaign).filter(
            AdCampaign.channel_id == data["channel_id"],
            AdCampaign.is_active == True,
            AdCampaign.scheduled_hours.like(f"%{data['hour']}%")
        ).all()

        return [a.video_url for a in ads]

    finally:
        db.close()


# ================= CLEANUP ================= #

@activity.defn
async def cleanup_old_videos_activity() -> str:
    video_dir = "/app/videos"

    if not os.path.exists(video_dir):
        return "No directory"

    now = time.time()
    count = 0

    for f in os.listdir(video_dir):
        path = os.path.join(video_dir, f)
        if os.path.isfile(path) and os.path.getmtime(path) < now - 86400:
            try:
                os.remove(path)
                count += 1
            except Exception:
                pass

    return f"Deleted {count} files"