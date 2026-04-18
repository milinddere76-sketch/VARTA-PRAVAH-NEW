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
        # Bootstrap with promo
        streamer.update_playlist("/app/videos/promo.mp4")
        
        while True:
            if not queue.empty():
                item = queue.get()
                video = item["video"]
                print(f"📺 [MCR] Now Playing Bulletin: {video}")
                streamer.is_promo = False
                streamer.update_playlist(video)
                
                # Wait for video to finish (or approx time)
                # We monitor the process until it exits
                while streamer.process and streamer.process.poll() is None:
                    time.sleep(5)
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
                    # Keep the heartbeat alive with a lighter loop if needed
                    # But streamer.sh -stream_loop -1 handles this!
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
