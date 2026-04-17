import os
import time
import glob

# Configuration
VIDEOS_DIR = "/app/videos"
PLAYLIST_PATH = "/app/videos/playlist.txt"
PROMO_PATH = "/app/videos/promo.mp4"
STANDBY_PATH = "/app/videos/promo.mp4" # Using promo as standby if dedicated fails

def is_ready(file_path):
    """Ensures the file exists and is large enough to be a valid video (prevents partial reads)."""
    return os.path.exists(file_path) and os.path.getsize(file_path) > 500000

def get_latest_video():
    """Finds the most recently created news video."""
    files = glob.glob(os.path.join(VIDEOS_DIR, "news_*.mp4"))
    if not files:
        return None
    # Returns the file with the latest creation time
    return max(files, key=os.path.getctime)

def update_playlist(videos):
    """Atomically updates the FFmpeg-compatible concat playlist."""
    tmp_path = PLAYLIST_PATH + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            for v in videos:
                # Ensure path is absolute for FFmpeg inside container
                abs_v = v if v.startswith("/") else os.path.join("/app", v)
                if os.path.exists(abs_v):
                    # FFmpeg concat demuxer format
                    f.write(f"file '{abs_v}'\n")
        
        # Atomic swap to avoid reading a partial playlist
        os.replace(tmp_path, PLAYLIST_PATH)
        return True
    except Exception as e:
        print(f"❌ Playlist update failed: {e}")
        return False

# Global State for Branding
LAST_INTRO_TIME = 0 # Epoch time of last intro play
INTRO_PATH = "/app/videos/intro.mp4"

def run_switcher():
    global LAST_INTRO_TIME
    print("📺 [SWITCHER] Active - Monitoring /app/videos/news_*.mp4")
    
    while True:
        try:
            current_time = time.time()
            
            # 0. IMMEDIATE BREAKING NEWS PRIORITY
            breaking_path = "/app/videos/news_breaking.mp4"
            if os.path.exists(breaking_path) and is_ready(breaking_path):
                print(f"🚨 [SWITCHER] {time.ctime()} | FLASH PRIORITY: BREAKING NEWS BUMPER!")
                update_playlist([breaking_path])
                # We wait 20 seconds for it to broadcast
                time.sleep(20)
                try:
                    os.remove(breaking_path)
                except: pass
                continue

            # 1. CHANNEL INTRO (Startup or Hourly Branding Refresh)
            # Plays if never played OR if 3600 seconds (1 hour) have passed
            if current_time - LAST_INTRO_TIME > 3600:
                if os.path.exists(INTRO_PATH):
                    print(f"🎬 [SWITCHER] {time.ctime()} | Playing Channel Intro & Branding...")
                    update_playlist([
                        INTRO_PATH,
                        STANDBY_PATH
                    ])
                    LAST_INTRO_TIME = current_time
                    # Allow intro (usually 15-60s) to play before switching to news
                    time.sleep(60)
                    continue

            # 2. NORMAL PRODUCTION FLOW
            latest = get_latest_video()

            if latest and is_ready(latest):
                print(f"📰 [SWITCHER] {time.ctime()} | BROADCASTING: {os.path.basename(latest)}")

                # THE ULTIMATE PIPELINE: 
                # 1. Start with News Bulletin
                # 2. Transition immediately to Advertising/Promo
                update_playlist([
                    latest,
                    PROMO_PATH # This acts as our 'Ad' segment
                ])

                # Wait for the bulletin cycle (approx 5 mins) before re-checking
                time.sleep(300)

            else:
                # No news found, stick to standby/promo
                print(f"⏳ [SWITCHER] {time.ctime()} | No news found. Playing standby.")
                update_playlist([STANDBY_PATH])
                time.sleep(30)
                
        except Exception as e:
            print(f"⚠️ [SWITCHER] Loop error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_switcher()
