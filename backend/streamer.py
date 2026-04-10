import os
import subprocess
import time
from pathlib import Path
import sys
import threading


class Streamer:
    def __init__(self, youtube_key: str, channel_id: int):
        self.youtube_key = youtube_key
        self.channel_id = channel_id
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{youtube_key}"
        self.current_video = None
        self.process = None
        self.monitor_thread = None
        self.stop_event = threading.Event()

    def create_initial_playlist(self, initial_video: str):
        self.current_video = initial_video

    def update_playlist(self, new_video: str):
        self.current_video = new_video
        self.stop_stream()
        self.start_stream()

    def start_stream(self):
        if not self.current_video:
            raise ValueError("No video file set for streaming")

        # ✅ FIX: check file exists
        if not os.path.exists(self.current_video):
            raise FileNotFoundError(f"Video not found: {self.current_video}")

        # Detect logo
        logo_path = None
        for candidate in ["/app/logo.png", "/app/logo.jpg"]:
            if os.path.exists(candidate):
                logo_path = candidate
                break

        # Base command
        command = [
            "ffmpeg",
            "-re",
            "-stream_loop", "-1",
            "-i", self.current_video,
        ]

        # Add logo if exists
        if logo_path:
            command += [
                "-i", logo_path,
                "-filter_complex",
                "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2[scaled];"
                "[1:v]scale=150:-1[logo];"
                "[scaled][logo]overlay=W-w-10:10[outv]",
                "-map", "[outv]",
                "-map", "0:a?"
            ]
        else:
            command += [
                "-vf",
                "scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2"
            ]

        # Output settings (YouTube optimized)
        command += [
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", "2500k",
            "-maxrate", "2500k",
            "-bufsize", "5000k",
            "-pix_fmt", "yuv420p",
            "-g", "50",
            "-c:a", "aac",
            "-ar", "44100",
            "-b:a", "128k",
            "-f", "flv",
            self.rtmp_url
        ]

        print(f"🚀 Starting stream: {self.current_video}", flush=True)

        # ✅ FIX: Capture stderr to help debug conversion/auth issues
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Start a thread to read logs so they appear in docker logs
        threading.Thread(target=self._read_logs, daemon=True).start()

        # ✅ AUTO-RESTART LOOP (NON-BLOCKING)
        self.stop_event.clear()
        if not self.monitor_thread or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
            self.monitor_thread.start()

    def _read_logs(self):
        """Forward FFmpeg output to sys.stdout"""
        if not self.process:
            return
        for line in iter(self.process.stdout.readline, ''):
            if self.stop_event.is_set():
                break
            # Filter out too much noise but keep errors
            if "error" in line.lower() or "warning" in line.lower() or "frame=" in line[:6]:
                print(f"[FFMPEG] {line.strip()}", flush=True)

    def _monitor(self):
        """Restart FFmpeg if it stops unexpectedly"""
        while not self.stop_event.is_set():
            if self.process and self.process.poll() is not None:
                # Process stopped
                if not self.stop_event.is_set():
                    print("⚠️ FFmpeg process stopped unexpectedly. Restarting in 5 seconds...", flush=True)
                    time.sleep(5)
                    try:
                        self.start_stream()
                    except Exception as e:
                        print(f"❌ Failed to restart stream: {e}", flush=True)
                break
            time.sleep(2)

    def stop_stream(self):
        self.stop_event.set()
        if self.process:
            print("🛑 Stopping stream process...", flush=True)
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