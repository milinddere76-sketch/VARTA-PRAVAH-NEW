import os
import subprocess
import time
import tempfile
from pathlib import Path
import sys
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

    def create_initial_playlist(self, initial_video: str):
        self.current_video = initial_video

    def update_playlist(self, new_video: str):
        self.current_video = new_video
        self.stop_stream()
        time.sleep(2)
        self.start_stream()

    def _build_ffmpeg_cmd(self) -> list:
        """
        Build a YouTube-optimised FFmpeg command.

        Key settings:
        - gapless infinite loop via concat demuxer (no gaps between loops)
        - -r 30  : enforce constant 30 fps output — YouTube requires this
        - -g 60  : keyframe every 2 s at 30 fps (YouTube recommendation)
        - -keyint_min 60 / -sc_threshold 0 : no scene-change keyframes
        - ultrafast preset + 1500k bitrate : leaves CPU headroom on the VPS
        - flvflags no_duration_filesize : required for live streaming
        """
        video = self.current_video

        # Create a temp concat file so FFmpeg loops without gaps
        concat_path = f"/tmp/loop_{self.channel_id}.txt"
        # Write enough repetitions that FFmpeg never reaches the end
        with open(concat_path, "w") as f:
            for _ in range(9999):
                f.write(f"file '{video}'\n")

        cmd = [
            "ffmpeg",
            "-y",                        # overwrite any temp files
            "-loglevel", "warning",      # reduce noise, keep errors visible
            "-re",                       # read at native playback speed
            "-f",  "concat",             # gapless concat (no stream_loop gaps)
            "-safe", "0",
            "-i",  concat_path,
        ]

        # Detect logo overlay
        logo_path = None
        for candidate in ["/app/logo.png", "/app/logo.jpg"]:
            if os.path.exists(candidate):
                logo_path = candidate
                break

        if logo_path:
            cmd += [
                "-i", logo_path,
                "-filter_complex",
                "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                "fps=30[scaled];"
                "[1:v]scale=120:-1[logo];"
                "[scaled][logo]overlay=W-w-10:10[outv]",
                "-map", "[outv]",
                "-map", "0:a?",      # ← explicit audio map
            ]
        else:
            cmd += [
                "-map", "0:v",       # ← explicit video map
                "-map", "0:a?",      # ← explicit audio map (? = optional so no crash if missing)
                "-vf",
                "scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                "fps=30",
            ]

        cmd += [
            # Video — YouTube 720p recommended settings
            "-c:v",        "libx264",
            "-preset",     "veryfast",     # better compression than ultrafast at same CPU
            "-tune",       "zerolatency",
            "-r",          "30",
            "-g",          "60",           # keyframe every 2 s
            "-keyint_min", "60",
            "-x264opts",   "scenecut=0",   # no random keyframes
            "-b:v",        "2500k",        # YouTube recommended for 720p
            "-maxrate",    "3000k",
            "-bufsize",    "6000k",        # 2× maxrate
            "-pix_fmt",    "yuv420p",
            # Audio — explicit settings, must be present
            "-c:a",  "aac",
            "-ar",   "44100",
            "-b:a",  "128k",
            "-ac",   "2",                  # force stereo
            # Output
            "-f",        "flv",
            "-flvflags", "no_duration_filesize",
            self.rtmp_url,
        ]
        return cmd

    def start_stream(self):
        if not self.current_video:
            raise ValueError("No video file set for streaming")
        if not os.path.exists(self.current_video):
            raise FileNotFoundError(f"Video not found: {self.current_video}")

        cmd = self._build_ffmpeg_cmd()
        print(f"🚀 Starting stream → {self.rtmp_url}", flush=True)
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
        """Forward FFmpeg output to stdout — always print errors."""
        if not self.process:
            return
        for line in iter(self.process.stdout.readline, ""):
            if self.stop_event.is_set():
                break
            line = line.strip()
            if not line:
                continue
            # Always print errors/warnings; sample frame stats
            low = line.lower()
            if any(k in low for k in ("error", "warning", "failed", "invalid", "connection")):
                print(f"[FFMPEG ERROR] {line}", flush=True)
            elif line.startswith("frame="):
                print(f"[FFMPEG] {line}", flush=True)

    def _monitor(self):
        """Auto-restart FFmpeg if it exits unexpectedly."""
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
            except Exception as e:
                print(f"Error stopping process: {e}")
            self.process = None


if __name__ == "__main__":
    print("Streamer module loaded.")