import os
import subprocess
import time
from pathlib import Path

class Streamer:
    def __init__(self, youtube_key: str, channel_id: int):
        self.youtube_key = youtube_key
        self.channel_id = channel_id
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{youtube_key}"
        self.playlist_path = f"playlist_{channel_id}.txt"
        self.process = None

    def create_initial_playlist(self, initial_video: str):
        """Creates a playlist file that loops the initial video."""
        with open(self.playlist_path, "w") as f:
            f.write(f"file '{initial_video}'\n")
            f.write(f"file '{initial_video}'\n")  # Loop buffer

    def update_playlist(self, new_video: str):
        """Updates the playlist to point to the new video for the next loop."""
        # FFmpeg with -stream_loop -1 and -f concat -safe 0 -i playlist.txt
        # will read the file once and loop. To hot-swap, we need a more 
        # advanced approach or just overwrite and let the next loop pick it up.
        with open(self.playlist_path, "w") as f:
            f.write(f"file '{new_video}'\n")

    def start_stream(self):
        """Starts the FFmpeg process."""
        # Command explaining:
        # -re: Read input at native frame rate
        # -f concat: Concatenate files in playlist
        # -safe 0: Allow absolute paths
        # -stream_loop -1: Loop the input indefinitely
        # -c:v copy -c:a copy: Pass through codecs (fast, low CPU)
        # -f flv: Format for RTMP
        
        command = [
            "ffmpeg",
            "-y", # Overwrite output if exists (though RTMP doesn't)
            "-protocol_whitelist", "file,crypto,data,https,tcp,tls",
            "-re",
            "-f", "concat",
            "-safe", "0",
            "-i", self.playlist_path,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", "3000k",
            "-maxrate", "3000k",
            "-bufsize", "6000k",
            "-pix_fmt", "yuv420p", # Standard for most players
            "-c:a", "aac",
            "-ar", "44100",
            "-f", "flv",
            self.rtmp_url
        ]
        
        print(f"Starting stream to {self.rtmp_url}...", flush=True)
        # By removing the PIPE argument, Python allows FFmpeg to natively print raw speed heuristics to the Docker Daemon logs
        self.process = subprocess.Popen(command)

    def stop_stream(self):
        if self.process:
            self.process.terminate()
            print("Stream stopped.")

if __name__ == "__main__":
    # Test stub
    YOUTUBE_KEY = "your-key-here"
    VIDEO = "c:/VARTAPRAVAH/assets/test_video.mp4"
    
    streamer = Streamer(YOUTUBE_KEY, channel_id=99)
    streamer.create_initial_playlist(VIDEO)
    streamer.start_stream()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        streamer.stop_stream()
