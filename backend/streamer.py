import os
import subprocess
import time
import threading


class Streamer:
    def __init__(self, youtube_key: str, channel_id: int):
        self.youtube_key  = youtube_key
        self.channel_id   = channel_id
        self.rtmp_url     = f"rtmp://a.rtmp.youtube.com/live2/{youtube_key}"
        self.current_video = None
        self.process       = None
        self.monitor_thread = None
        self.stop_event    = threading.Event()
        
        # Dynamic assets mapping (Docker vs Local)
        here = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(here, "logo.png")
        self.is_promo = False

    def create_initial_playlist(self, initial_video: str):
        self.current_video = initial_video

    def update_playlist(self, new_video: str):
        self.current_video = new_video
        self.stop_stream()
        time.sleep(2)
        self.start_stream()

    def _get_has_audio(self) -> bool:
        """Probe the video file to check if it contains any audio streams."""
        if not self.current_video or not os.path.exists(self.current_video):
            return False
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", self.current_video]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            # Check if 'audio' is present in the output (e.g. video\naudio or just video)
            return "audio" in res.stdout.strip().split("\n")
        except:
            return False

    def _build_ffmpeg_cmd(self) -> list:
        has_audio = self._get_has_audio()
        
        # Base CMD (Zero-CPU Push)
        cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-progress", "-", "-re"]
        
        # Input 0: Main Video
        if "=" in self.current_video and " " not in self.current_video:
            cmd += ["-f", "lavfi", "-i", self.current_video]
        else:
            cmd += ["-i", self.current_video]
        
        # Input 1: Always provide silence as a fallback
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

        # ── Dynamic Encoding Selection ────────────────────────────
        # MP4 files (baked) should be copied; everything else (lavfi, standby) must be encoded.
        is_lavfi = not str(self.current_video).lower().endswith(".mp4")

        
        if is_lavfi:
            cmd += [
                "-map", "0:v", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
                "-r", "30", "-g", "60", "-keyint_min", "60",
                "-x264opts", "scenecut=0:nal-hrd=cbr", "-b:v", "2500k", "-minrate", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
                "-pix_fmt", "yuv420p"
            ]
        else:
            cmd += ["-map", "0:v", "-c:v", "copy"]

        # Audio handling: copy if available in file, encode if lavfi/standby
        if has_audio and not is_lavfi:
            cmd += ["-map", "0:a", "-c:a", "copy"]
        else:
            # For standby or files without audio, use Input 1 (anullsrc)
            cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"]


        cmd += [
            "-metadata", f"vp_channel={self.channel_id}",
            "-f", "flv", "-flvflags", "no_duration_filesize",
            self.rtmp_url,
        ]
        return cmd



    def enqueue_video(self, video_path: str):
        """Sets the next video to play after the current one finishes."""
        self.next_video = video_path
        print(f"--- [QUEUE] Enqueued for Next: {video_path} ---")

    def start_stream(self):
        if not self.current_video:
            raise ValueError("No video file set for streaming")
        
        final_video = os.path.abspath(self.current_video)
        if not os.path.exists(final_video) and "color=" not in final_video:
            print(f"  {final_video} not found yet. Using emergency standby pattern.", flush=True)
            final_video = "color=c=0x081122:s=1280x720:r=30[bg];[bg]drawgrid=w=0:h=8:c=black@0.1:t=1[out]"
            self.current_video = final_video
        else:
            self.current_video = final_video
        
        cmd = self._build_ffmpeg_cmd()
        print(f" Starting stream  {self.rtmp_url}", flush=True)
        print(f"   Source: {self.current_video}", flush=True)

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        threading.Thread(target=self._read_logs, daemon=True).start()

        self.stop_event.clear()
        if not self.monitor_thread or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
            self.monitor_thread.start()

    def _read_logs(self):
        if not self.process: return
        for line in iter(self.process.stdout.readline, ""):
            if self.stop_event.is_set(): break
            line = line.strip()
            if not line: continue
            low = line.lower()
            # Print all status lines to monitor 'speed' and 'bitrate' in real-time
            # Print progress lines (out_time, bitrate, speed) for real-time monitoring
            if any(k in line for k in ("out_time=", "bitrate=", "speed=", "error", "warning")):
                print(f"[STREAM] {line}", flush=True)

    def _monitor(self):
        while not self.stop_event.is_set():
            if self.process and self.process.poll() is not None:
                if not self.stop_event.is_set():
                    # Process exited naturally (video finished) or crashed
                    if hasattr(self, 'next_video') and self.next_video:
                        print(f"--- [TRANSITION] Playing next in queue: {self.next_video} ---")
                        self.current_video = self.next_video
                        self.next_video = None
                    else:
                        print(f"--- [LOOP] Video finished. Re-playing current: {self.current_video} ---")
                    
                    time.sleep(1) # Small gap to allow YouTube to stabilize
                    try:
                        self.start_stream()
                        return 
                    except Exception as e:
                        print(f"❌ Restart failed: {e}", flush=True)
            time.sleep(2)


    def stop_stream(self):
        self.stop_event.set()
        if self.process:
            print("🛑 Stopping FFmpeg…", flush=True)
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except:
                pass
            self.process = None

if __name__ == "__main__":
    print("Streamer module loaded.")