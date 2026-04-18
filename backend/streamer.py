import os
import subprocess
import time
import threading
import signal

class Streamer:
    def __init__(self, youtube_key: str, channel_id: int):
        self.youtube_key = youtube_key
        self.channel_id = channel_id
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{youtube_key}"
        self.current_video = None
        
        self.main_process = None
        self.pumper_process = None
        self.pipe_path = "/tmp/mcr_pipe"
        
        self.monitor_thread = None
        self.pumper_thread = None
        self.stop_event = threading.Event()
        
        # Standardize assets
        self.is_promo = False
        self._setup_pipe()

    def _setup_pipe(self):
        """Creates the FIFO bridge."""
        if os.path.exists(self.pipe_path):
            os.remove(self.pipe_path)
        os.mkfifo(self.pipe_path)

    def update_playlist(self, new_video: str):
        """SWITCHER LOGIC: Changes content WITHOUT dropping the stream."""
        print(f"🔄 [STREAMER] Seamlessly switching to: {new_video}")
        self.current_video = new_video
        self._restart_pumper()

    def _restart_pumper(self):
        """Kills the current content pump and starts a new one into the persistent pipe."""
        if self.pumper_process:
            try:
                self.pumper_process.terminate()
                self.pumper_process.wait(timeout=2)
            except:
                try: self.pumper_process.kill()
                except: pass
        
        # Start new pumper
        cmd = [
            "ffmpeg", "-y", "-re",
            "-i", self.current_video,
            "-c:v", "copy", "-c:a", "copy",
            "-f", "flv", self.pipe_path
        ]
        
        # If it's a promo, loop it infinitely
        if "promo.mp4" in self.current_video or self.is_promo:
            cmd.insert(4, "-stream_loop")
            cmd.insert(5, "-1")

        self.pumper_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def start_stream(self):
        """AIR IGNITION: Starts the ONE AND ONLY stream to YouTube."""
        print(f"🚀 [STREAMER] Igniting Persistent YouTube Connection...")
        
        # Main persistent engine
        # It reads from the pipe and encodes for YouTube
        cmd = [
            "ffmpeg", "-y", "-loglevel", "warning",
            "-i", self.pipe_path,
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
            "-pix_fmt", "yuv420p", "-g", "60",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-f", "flv", self.rtmp_url
        ]

        self.main_process = subprocess.Popen(cmd)
        
        # Ensure we are pumping something immediately
        if not self.current_video:
            self.current_video = "/app/videos/promo.mp4"
        self._restart_pumper()

        # Supervision
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def _monitor(self):
        """Watchdog to ensure the main connection never dies."""
        while not self.stop_event.is_set():
            if self.main_process and self.main_process.poll() is not None:
                print("⚠️ [STREAMER] Main Stream crashed! Re-igniting...")
                self.start_stream()
                break
            time.sleep(5)

    def stop_stream(self):
        """Full Shutdown."""
        self.stop_event.set()
        for p in [self.pumper_process, self.main_process]:
            if p:
                try: p.terminate()
                except: pass
        if os.path.exists(self.pipe_path):
            os.remove(self.pipe_path)

if __name__ == "__main__":
    # Test boot
    print("Persistent Streamer Loaded.")