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
            old_streamer = streamer
            streamer = Streamer()  # Refresh the stream key from environment or DB
            try:
                old_streamer.stop_stream()  # Clean up old processes and pipe
            except Exception as e:
                print(f"⚠️ [MCR] Error cleaning up old streamer: {e}")

        # 🚀 Start the persistent YouTube signal
        if not streamer.start_stream():
            print("⚠️ [MCR] Stream startup failed. Retrying in 30s...")
            time.sleep(30)
            return self.run_loop()

        last_news = "/app/videos/promo.mp4"
        starvation_counter = 0
        
        while True:
            try:
                # 1. Check for NEW content arriving from the worker
                if not queue.empty():
                    starvation_counter = 0
                    item = queue.get()
                    video = item["video"]
                    print(f"📺 [MCR] ⬇️ INCOMING: {video}")
                    
                    # Verify file exists
                    if not os.path.exists(video):
                        print(f"❌ [MCR] Video not found: {video}")
                        continue
                    
                    fsize = os.path.getsize(video) / (1024*1024)
                    print(f"📊 [MCR] Size: {fsize:.1f}MB, Queue depth: {queue.qsize()}")
                    
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
                    starvation_counter += 1
                    if starvation_counter % 6 == 0:  # Log every 30 seconds
                        print(f"🔄 [MCR] Waiting for content... (queue empty for {starvation_counter*5}s)")
                    
                    # 2. Continuity: If nothing is in queue, ensure SOMETHING is playing
                    # If the pumper died (e.g. news finished), loop back to last known good news or promo
                    if not streamer.pumper_process or streamer.pumper_process.poll() is not None:
                        print(f"🕒 [MCR] Pumper ended. Bridging with: {os.path.basename(last_news)}")
                        streamer.is_promo = ("news_" not in last_news)
                        streamer.update_playlist(last_news)
                
                time.sleep(5)
            except Exception as e:
                print(f"⚠️ [MCR] Loop error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)

@app.get("/status")
async def status():
    """Health check endpoint for the broadcast controller."""
    return {
        "status": "online",
        "queue_size": queue.qsize(),
        "streaming": streamer.stream_ready(),
        "current_video": streamer.current_video,
        "processes": {
            "main": streamer.main_process.poll() is None if streamer.main_process else False,
            "pumper": streamer.pumper_process.poll() is None if streamer.pumper_process else False
        }
    }

@app.post("/add-video")
async def add_video(data: dict):
    video_path = data.get("video")
    if video_path and os.path.exists(video_path):
        file_size_mb = os.path.getsize(video_path) / (1024*1024)
        print(f"✅ [MCR] Video queued: {video_path} ({file_size_mb:.1f}MB), queue depth: {queue.qsize()}")
        queue.put({"video": video_path})
        return {"status": "queued", "queue_size": queue.qsize()}
    else:
        print(f"❌ [MCR] Invalid video path: {video_path}")
        return {"status": "error", "message": "File not found or invalid path"}

def start_mcr():
    ctrl = BroadcastController()
    thread = threading.Thread(target=ctrl.run_loop, daemon=True)
    thread.start()

if __name__ == "__main__":
    start_mcr()
    print(f"🚀 [MCR] Broadcast Controller listening on 0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
