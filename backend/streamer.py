import os
import subprocess
import time
import threading
import signal

class Streamer:
    PLACEHOLDER_KEYS = {
        "5w92-9u7p-ucjh-b1bx-bszv",
        "9efm-d8gq-mmma-9y1b-7sez",
        "your-stream-key-here",
        "key",
    }

    def __init__(self, youtube_key: str = None, channel_id: int = 1):
        # Auto-detect from environment if not provided (Industrial Standard)
        self.youtube_key = youtube_key or os.getenv("YOUTUBE_STREAM_KEY")
        self.channel_id = channel_id

        if not self.youtube_key and self.channel_id:
            db = None
            try:
                from database import get_session_local
                from models import Channel
                db = get_session_local()
                channel = db.query(Channel).filter(Channel.id == self.channel_id).first()
                if channel and channel.youtube_stream_key:
                    self.youtube_key = channel.youtube_stream_key
            except Exception as e:
                print(f"⚠️ [STREAMER] DB stream key lookup failed: {e}")
            finally:
                if db is not None:
                    try:
                        db.close()
                    except:
                        pass

        if self.youtube_key and self._is_placeholder_key(self.youtube_key):
            print("⚠️ [STREAMER] Placeholder stream key detected. Please configure a real YouTube stream key.")
            self.youtube_key = None

        if not self.youtube_key:
            print("⚠️ [STREAMER] No valid YouTube Key found! Entering Standby Mode.")
            self.rtmp_url = None
        else:
            self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{self.youtube_key}"

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

    def _is_placeholder_key(self, key: str) -> bool:
        if not key:
            return True
        if key in self.PLACEHOLDER_KEYS:
            return True
        if " " in key:
            return True
        return key.count("-") < 2

    def stream_ready(self) -> bool:
        return bool(self.youtube_key)

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
            cmd.insert(3, "-stream_loop")
            cmd.insert(4, "-1")

        print(f"🎬 [PUMPER] Executing: {' '.join(cmd)}")
        self.pumper_process = subprocess.Popen(cmd) # Allow logs to flow to docker log for debugging

    def update_ticker(self, headlines: list):
        """Dynamically updates the scrolling news ticker with character sanitization."""
        ticker_path = "/app/ticker.txt"
        
        # Aggressive cleaning of each headline to remove control chars/newlines
        clean_headlines = []
        for h in headlines:
            # Filter to keep only Marathi group, Alphanumeric, Space, and punctuation
            clean = "".join(c for c in h if c.isalnum() or c.isspace() or '\u0900' <= c <= '\u097F' or c in ".-*|!?,")
            clean_headlines.append(clean.strip())
            
        text = " | ".join(clean_headlines) if clean_headlines else "वार्ताप्रवाह - ताज्या घडामोडी"
        with open(ticker_path, "w", encoding="utf-8") as f:
            f.write(f" *** {text} *** ")
        print(f"📰 [STREAMER] Ticker Updated: {text[:50]}...")

    def _get_filter_complex(self):
        """
        Determines the correct filter chain based on content type.
        News bulletins (news_*.mp4) already have tickers, so we skip the overlay.
        Promos/Ads need the dynamic ticker injected.
        """
        if self.current_video and "news_" in self.current_video:
            # Bulletins already have baked-in UI
            return "copy"
        
        # Promos/Loops need the dynamic ticker overlay
        return (
            r"drawtext=fontfile=/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf:"
            r"textfile=/app/ticker.txt:reload=1:"
            r"x=w-mod(max(t\,0)*(w+tw)/20\,(w+tw)):y=h-50:"
            r"fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6:text_shaping=1"
        )

    def start_stream(self):
        """AIR IGNITION: Starts the ONE AND ONLY stream to YouTube."""
        print(f"🚀 [STREAMER] Igniting Persistent YouTube Connection...")
        
        if not os.path.exists("/app/ticker.txt"):
            self.update_ticker(["वार्ताप्रवाह - आपले स्वागत आहे"])

        # Main persistent engine - STRICT CBR for YouTube Health
        # Note: We use -vf defined by content type
        v_filter = self._get_filter_complex()
        
        cmd = [
            "ffmpeg", "-y", "-loglevel", "warning",
            "-i", self.pipe_path,
            "-vf", v_filter,
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-b:v", "2500k", "-minrate", "2500k", "-maxrate", "2500k", "-bufsize", "2500k",
            "-nal-hrd", "cbr",
            "-pix_fmt", "yuv420p", "-g", "50",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-f", "flv", "-flvflags", "no_duration_filesize", self.rtmp_url
        ]

        if not self.stream_ready():
            print("⚠️ [STREAMER] Cannot start stream because no valid YouTube stream key is configured.")
            return False

        print(f"🎬 [MAIN-STREAM] Connecting to YouTube with {v_filter[:20]}...")
        self.main_process = subprocess.Popen(cmd)
        
        # Ensure we are pumping something immediately
        if not self.current_video:
            self.current_video = "/app/videos/promo.mp4"
        self._restart_pumper()

        # Supervision
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()
        return True

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