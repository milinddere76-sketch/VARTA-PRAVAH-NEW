import os
import subprocess
import time
from pathlib import Path
import sys


class Streamer:
    def __init__(self, youtube_key: str, channel_id: int):
        self.youtube_key = youtube_key
        self.channel_id = channel_id
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{youtube_key}"
        self.current_video = None
        self.process = None

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

        # ✅ FIX: direct subprocess (NO bash loop)
        self.process = subprocess.Popen(
            command,
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        # ✅ AUTO-RESTART LOOP (SAFE WAY)
        self._monitor()

    def _monitor(self):
        """Restart FFmpeg if it stops"""
        while True:
            if self.process.poll() is not None:
                print("⚠️ Stream stopped. Restarting in 5 seconds...", flush=True)
                time.sleep(5)
                self.start_stream()
                break
            time.sleep(2)

    def stop_stream(self):
        if self.process:
            print("🛑 Stopping stream...", flush=True)
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None


if __name__ == "__main__":
    YOUTUBE_KEY