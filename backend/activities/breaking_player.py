import shutil
import os
import time
from temporalio import activity

@activity.defn(name="play_breaking")
async def play_breaking_activity() -> str:
    """
    Triggers a full-screen 'Breaking News' bumper.
    Copies the master bumper to a timestamped news file for the switcher to catch.
    """
    source = "/app/videos/breaking.mp4"
    destination = "/app/videos/news_breaking.mp4"
    
    if os.path.exists(source):
        print("🚨 [BREAKING] Deploying Full-Screen Bumper!")
        try:
            shutil.copy2(source, destination)
            return destination
        except Exception as e:
            print(f"❌ [BREAKING] Bumper copy failed: {e}")
            return "failed"
    else:
        print("⚠️ [BREAKING] bumper.mp4 missing. Skipping visual flash.")
        return "missing"
