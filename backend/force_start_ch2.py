import asyncio
from temporalio.client import Client
import time
import sys
import os

async def main():
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from database import get_session_local
    import models

    db = get_session_local()()
    channel = db.query(models.Channel).filter(models.Channel.id == 2).first()
    db.close()

    if not channel:
        print("Channel 2 not found in DB.")
        return

    # Using localhost for manual trigger from terminal
    client = await Client.connect("localhost:7233")
    workflow_id = f"FORCED_RESTART_CH2_{int(time.time())}"
    print(f"Starting workflow: {workflow_id} for channel {channel.id}")
    
    await client.start_workflow(
        "StartImmediateStreamWorkflow",
        {
            "channel_id": channel.id,
            "stream_key": channel.youtube_stream_key,
            "video_url": "videos/promo.mp4",
            "is_promo": True
        },
        id=workflow_id,
        task_queue="news-task-queue",
    )
    print("Workflow for Channel 2 started successfully.")

if __name__ == "__main__":
    asyncio.run(main())
