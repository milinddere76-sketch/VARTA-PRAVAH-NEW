import os
import glob

VIDEOS_DIR = "/app/videos"

def nuclear_reset():
    print("🧨 [NUCLEAR RESET] Flushing all legacy news assets...")
    
    # 1. Remove all old news videos
    news_videos = glob.glob(os.path.join(VIDEOS_DIR, "news_*.mp4"))
    for f in news_videos:
        try:
            os.remove(f)
            print(f"🗑️ Deleted: {os.path.basename(f)}")
        except Exception as e:
            print(f"❌ Failed to delete {f}: {e}")

    # 2. Remove all old news audio
    news_audio = glob.glob(os.path.join(VIDEOS_DIR, "news_*.mp3"))
    for f in news_audio:
        try:
            os.remove(f)
        except: pass

    # 3. Remove playlist to force fresh generation
    playlist = os.path.join(VIDEOS_DIR, "playlist.txt")
    if os.path.exists(playlist):
        os.remove(playlist)

    print("✅ [RESET] News buffer cleared. The station will now generate fresh news from scratch.")

if __name__ == "__main__":
    # If running inside Docker
    nuclear_reset()
