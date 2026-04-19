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

        global streamer
        while not streamer.stream_ready():
            print("⚠️ [MCR] No valid YouTube stream key found. Waiting 30s before retrying...")
            time.sleep(30)
            streamer = Streamer()  # Refresh the stream key from environment or DB

        # 🚀 Start the persistent YouTube signal
        if not streamer.start_stream():
            print("⚠️ [MCR] Stream startup failed. Retrying in 30s...")
            time.sleep(30)
            return self.run_loop()

        last_news = "/app/videos/promo.mp4"
        
        while True:
            # 1. Check for NEW content arriving from the worker
            if not queue.empty():
                item = queue.get()
                video = item["video"]
                print(f"📺 [MCR] Incoming Content: {video}")
                
                # Update memory
                if "news_" in video:
                    last_news = video
                
                # Switch the stream pumper to the new video
                # Note: update_playlist() handles killing the old pumper
                streamer.is_promo = ("news_" not in video)
                streamer.update_playlist(video)
                
                # We don't block here anymore. We let the loop continue 
                # to monitor for even newer breaking news.
                time.sleep(2)
            
            else:
                # 2. Continuity: If nothing is in queue, ensure SOMETHING is playing
                # If the pumper died (e.g. news finished), loop back to last known good news or promo
                if not streamer.pumper_process or streamer.pumper_process.poll() is not None:
                    print(f"🕒 [MCR] Content ended. Bridging with: {last_news}")
                    streamer.is_promo = ("news_" not in last_news)
                    streamer.update_playlist(last_news)
            
            time.sleep(5)

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
