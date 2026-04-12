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

    def _build_ffmpeg_cmd(self, start_time: str = None) -> list:
        has_audio = self._get_has_audio()
        
        # Base CMD
        cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-re"]
        
        if start_time:
            cmd += ["-ss", start_time]

        # Input 0: Main Video or Standby Pattern
        # Check if it's a file path or a lavfi filter string
        if "=" in self.current_video and " " not in self.current_video:
            cmd += ["-f", "lavfi", "-i", self.current_video]
        else:
            cmd += ["-i", self.current_video]
        
        # Input 1: Fallback Silence (only used if 0:a is missing)
        if not has_audio:
            cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

        # Selection logic
        audio_map = "0:a" if has_audio else "1:a"

        # ── Video/Audio Mappings ──────────────────────────────────
        if self.is_promo:
            # Promo logic — simple loop
            cmd += [
                "-stream_loop", "-1",
                "-map", "0:v",
                "-map", audio_map,
                "-vf", "scale=1280:720,format=yuv420p,fps=30",
            ]
        elif os.path.exists(self.logo_path):
            # Input 2: Logo (if anullsrc occupied index 1) or Input 1 (if audio present)
            logo_idx = 2 if not has_audio else 1
            cmd += ["-i", self.logo_path]
            cmd += [
                "-filter_complex",
                f"[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30[scaled];"
                f"[{logo_idx}:v]scale=120:-1[logo];"
                f"[scaled][logo]overlay=W-w-10:10[outv]",
                "-map", "[outv]",
                "-map", audio_map,
            ]
        else:
            cmd += [
                "-map", "0:v",
                "-map", audio_map,
                "-vf",
                "scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                "format=yuv420p,fps=30",
            ]

        # YouTube recommended settings (720p CBR)
        cmd += [
            "-c:v",        "libx264",
            "-preset",     "ultrafast",       # Lower CPU usage for dual-channel
            "-tune",       "zerolatency",
            "-threads",    "2",                # Isolate CPU usage
            "-r",          "30",
            "-g",          "60",
            "-keyint_min", "60",
            "-x264opts",   "scenecut=0:nal-hrd=cbr",
            "-b:v",        "2500k",
            "-minrate",    "2500k",
            "-maxrate",    "2500k",
            "-bufsize",    "5000k",            # Larger buffer for stability
            "-pix_fmt",    "yuv420p",
            # Audio
            "-c:a",  "aac",
            "-ar",   "44100",
            "-b:a",  "128k",
            "-ac",   "2",
            # Metadata to identify the process for pkill -f
            "-metadata", f"vp_channel={self.channel_id}",
            "-f",        "flv",
            "-flvflags", "no_duration_filesize",
            self.rtmp_url,
        ]
        return cmd

    def start_stream(self):
        if not self.current_video:
            raise ValueError("No video file set for streaming")
        
        # ── EMERGENCY FALLBACK ──
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
        if not self.process:
            return
        for line in iter(self.process.stdout.readline, ""):
            if self.stop_event.is_set():
                break
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if any(k in low for k in ("error", "warning", "failed", "invalid", "connection")):
                print(f"[FFMPEG ERROR] {line}", flush=True)
            elif line.startswith("frame="):
                # Optionally print every Nth frame log or just stay quiet
                pass

    def _monitor(self):
        while not self.stop_event.is_set():
            if self.process and self.process.poll() is not None:
                if not self.stop_event.is_set():
                    rc = self.process.returncode
                    print(f"⚠️  FFmpeg exited (code {rc}). Restarting in 5 s…", flush=True)
                    time.sleep(5)
                    try:
                        self.start_stream()
                    except Exception as e:
                        print(f"❌ Restart failed: {e}", flush=True)
                break
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