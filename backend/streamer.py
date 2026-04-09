import os
import subprocess
import time
from pathlib import Path

class Streamer:
    def __init__(self, youtube_key: str, channel_id: int):
        self.youtube_key = youtube_key
        self.channel_id = channel_id
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{youtube_key}"
        self.current_video = None
        self.process = None

    def create_initial_playlist(self, initial_video: str):
        """Set the initial video to stream."""
        self.current_video = initial_video

    def update_playlist(self, new_video: str):
        """Updates the video to stream."""
        self.current_video = new_video
        # Kill current stream so it restarts with new video
        self.stop_stream()

    def start_stream(self):
        """Starts the FFmpeg process."""
        if not self.current_video:
            raise ValueError("No video file set for streaming")

        logo_path = None
        for candidate in ["/app/logo.png", "/app/logo.svg"]:
            if os.path.exists(candidate):
                logo_path = candidate
                break

        if self.current_video.startswith("/app/") and logo_path:
            command = [
                "ffmpeg",
                "-y",
                "-re",  # Read input at native frame rate
                "-stream_loop", "-1",  # Loop the input indefinitely
                "-i", self.current_video,
                "-i", logo_path,
                "-filter_complex", "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[scaled];[1:v]scale=200:-1[logo];[scaled][logo]overlay=W-w-20:20:format=auto[outv]",
                "-map", "[outv]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "2500k",
                "-maxrate", "2500k",
                "-minrate", "2500k",
                "-bufsize", "5000k",
                "-nal-hrd", "cbr",  # Force constant bitrate
                "-g", "60",  # Force keyframes every 2 seconds
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-ar", "44100",
                "-b:a", "128k",
                "-ac", "2",
                "-f", "flv",
                self.rtmp_url
            ]
        else:
            command = [
                "ffmpeg",
                "-y",
                "-re",  # Read input at native frame rate
                "-stream_loop", "-1",  # Loop the input indefinitely
                "-i", self.current_video,
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "2500k",
                "-maxrate", "2500k",
                "-minrate", "2500k",
                "-bufsize", "5000k",
                "-nal-hrd", "cbr",  # Force constant bitrate
                "-g", "60",  # Force keyframes every 2 seconds
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-ar", "44100",
                "-b:a", "128k",
                "-ac", "2",
                "-f", "flv",
                self.rtmp_url
            ]

        print(f"Starting stream to {self.rtmp_url} with video {self.current_video}...", flush=True)
        # By providing sys.stdout/stderr, we guarantee the sub-process output hits the Docker logs
        import sys

        # Convert the command list to a bash string
        cmd_str = " ".join([f"'{c}'" if (" " in c or "=" in c) else c for c in command])

        # Super-robust Endless Restart Wrapper
        bash_loop = f"while true; do {cmd_str}; echo '⚠️ Temporal Stream disconnected. Auto-recovering in 5 seconds...'; sleep 5; done"

        self.process = subprocess.Popen(bash_loop, shell=True, executable='/bin/bash', stdout=sys.stdout, stderr=sys.stderr)

    def stop_stream(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("Stream stopped.")

if __name__ == "__main__":
    # Test stub
    YOUTUBE_KEY = "your-key-here"
    VIDEO = "/app/videos/promo.mp4"
    
    streamer = Streamer(YOUTUBE_KEY, channel_id=99)
    streamer.create_initial_playlist(VIDEO)
    streamer.start_stream()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        streamer.stop_stream()