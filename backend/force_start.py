import asyncio
from temporalio.client import Client
import time

async def main():
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from database import get_session_local
    import models

    db = get_session_local()()
    channel = db.query(models.Channel).first()
    db.close()

    if not channel:
        print("No channel found in DB.")
        return

    client = await Client.connect("temporal:7233")
    workflow_id = f"FORCED_RESTART_CH1_{int(time.time())}"
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
    print("Workflow started successfully.")

if __name__ == "__main__":
    asyncio.run(main())
