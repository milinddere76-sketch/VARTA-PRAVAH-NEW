import time
import threading
import os
from queue import Queue
from streamer import Streamer
from fastapi import FastAPI, BackgroundTasks
import uvicorn

app = FastAPI()
queue = Queue()
streamer = Streamer()
last_promo_time = time.time()

class BroadcastController:
    def __init__(self):
        self.last_promo_time = time.time()

    def run_loop(self):
        print("🎬 [MCR] Master Broadcast Control active.")
        
        # 🚀 IMMEDIATE POWER-ON: Ignite the YouTube signal at boot
        streamer.start_stream()
        
        last_news = "/app/videos/promo.mp4" # Initial fallback
        
        while True:
            if not queue.empty():
                item = queue.get()
                video = item["video"]
                print(f"📺 [MCR] Now Playing Bulletin: {video}")
                
                # Update memory
                if "news_" in video:
                    last_news = video
                
                streamer.is_promo = False
                streamer.update_playlist(video)
                
                # Wait for the specific video (pumper) to finish, NOT the persistent stream
                while streamer.pumper_process and streamer.pumper_process.poll() is None:
                    time.sleep(2)
            else:
                # 📢 Continuity Mode
                current_time = time.time()
                if current_time - self.last_promo_time > 300: # 5 min rule
                    print("📢 [MCR] Injecting scheduled promo.")
                    streamer.is_promo = True
                    streamer.update_playlist("/app/videos/promo.mp4")
                    self.last_promo_time = current_time
                    time.sleep(30)
                else:
                    # 🕒 REPLAY LAST NEWS (Zero-Silence Logic)
                    print(f"🕒 [MCR] Queue empty. Replaying: {last_news}")
                    streamer.update_playlist(last_news)
                    time.sleep(10)

@app.post("/add-video")
async def add_video(data: dict):
    video_path = data.get("video")
    if video_path and os.path.exists(video_path):
        queue.put({"video": video_path})
        return {"status": "queued"}
    return {"status": "error", "message": "File not found"}

def start_mcr():
    ctrl = BroadcastController()
    thread = threading.Thread(target=ctrl.run_loop, daemon=True)
    thread.start()

if __name__ == "__main__":
    start_mcr()
    uvicorn.run(app, host="0.0.0.0", port=8001)
