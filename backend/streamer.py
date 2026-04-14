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
        
        here = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(here, "logo.png")

    def create_initial_playlist(self, initial_video: str):
        self.current_video = initial_video

    def _get_has_audio(self) -> bool:
        if not self.current_video or not os.path.exists(self.current_video):
            return False
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", self.current_video]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return "audio" in res.stdout.strip().split("\n")
        except:
            return False

    def _build_ffmpeg_cmd(self) -> list:
        has_audio = self._get_has_audio()
        is_mp4 = str(self.current_video).lower().endswith(".mp4")
        
        # Base CMD
        # -re MUST be used for live streaming to enforce 1x speed
        cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-progress", "-"]
        
        # Input 0: Main Video
        if "=" in str(self.current_video) and " " not in str(self.current_video):
            # For virtual sources (lavfi)
            cmd += ["-re", "-f", "lavfi", "-i", self.current_video]
        else:
            # For files
            cmd += ["-re", "-i", self.current_video]
        
        # Input 1: Always provide silence fallback
        cmd += ["-re", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

        if not is_mp4:
            # Re-encode for non-mp4 (like the standby color pattern)
            cmd += [
                "-map", "0:v", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
                "-r", "30", "-g", "60", "-keyint_min", "60",
                "-x264opts", "scenecut=0:nal-hrd=cbr", "-b:v", "6800k", "-minrate", "6800k", "-maxrate", "6800k", "-bufsize", "13600k",
                "-pix_fmt", "yuv420p"
            ]
        else:
            cmd += [
                "-map", "0:v", "-c:v", "copy"
            ]

        # Audio handling
        if has_audio and is_mp4:
            cmd += ["-map", "0:a", "-c:a", "aac", "-b:a", "128k"]
        else:
            cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"]

        cmd += [
            "-f", "flv", "-flvflags", "no_duration_filesize",
            self.rtmp_url,
        ]
        return cmd

    def start_stream(self):
        if not self.current_video:
            raise ValueError("No video file set for streaming")
        
        final_video = os.path.abspath(self.current_video)
        if not os.path.exists(final_video) and "color=" not in final_video:
            print(f"  {final_video} not found. Standby.", flush=True)
            final_video = "color=c=0x081122:s=1280x720:r=30[bg];[bg]drawgrid=w=0:h=8:c=black@0.1:t=1[out]"
            self.current_video = final_video
        else:
            self.current_video = final_video
        
        cmd = self._build_ffmpeg_cmd()
        print(f" Starting stream on Channel {self.channel_id}", flush=True)

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
            if any(k in line for k in ("out_time=", "bitrate=", "speed=")):
                print(f"[CH{self.channel_id}] {line.strip()}", flush=True)

    def _monitor(self):
        while not self.stop_event.is_set():
            if self.process and self.process.poll() is not None:
                if not self.stop_event.is_set():
                    print(f"--- [LOOP] Restarting Stream for Channel {self.channel_id} ---")
                    time.sleep(2)
                    self.start_stream()
                    return
            time.sleep(5)

    def stop_stream(self):
        self.stop_event.set()
        if self.process:
            print(f"🛑 Stopping FFmpeg for Channel {self.channel_id}…", flush=True)
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try: self.process.kill()
                except: pass
            self.process = None

if __name__ == "__main__":
    print("Streamer module loaded.")