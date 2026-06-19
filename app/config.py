import os
from dotenv import load_dotenv

load_dotenv()

# --- REDIS CONFIG ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
QUEUE_NAME = "news_queue"

# --- POSTGRES CONFIG ---
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "vartapravah")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "password")

# --- API KEYS ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
STREAM_KEY = os.getenv("YOUTUBE_STREAM_KEY", "qcu7-xesd-m4sv-9zvv-e335")


# --- ORACLE CLOUD (RELAY) CONFIG ---
ORACLE_IP = os.getenv("ORACLE_IP", "")
ORACLE_USER = os.getenv("ORACLE_USER", "ubuntu")
ORACLE_KEY_PATH = os.getenv("ORACLE_KEY_PATH", "/app/oracle_key.key")
ORACLE_VIDEO_DIR = os.getenv("ORACLE_VIDEO_DIR", "/home/ubuntu/videos")
ORACLE_QUEUE_DIR = os.getenv("ORACLE_QUEUE_DIR", "/home/ubuntu/queue")

# --- MODEL CONFIG ---
TTS_MODEL = os.getenv("TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")

# --- RESOURCE MANAGEMENT ---
MAX_WORKERS = 1  # SadTalker is VRAM intensive

# --- PATHS ---
ASSETS_DIR = "/app/assets"
OUTPUT_DIR = "/app/output"

# Ensure directories exist
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"📂 [CONFIG] Assets: {ASSETS_DIR}")
print(f"📂 [CONFIG] Output: {OUTPUT_DIR}")
