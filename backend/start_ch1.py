import asyncio
import os
import sys

# Add current dir to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import temporal_utils
from streaming_engine.workflows import MasterBulletinWorkflow
from database import get_session_local
import models

async def run():
    client = await temporal_utils.get_temporal_client()
    db = get_session_local()()
    ch = db.query(models.Channel).filter(models.Channel.id == 1).first()
    db.close()
    
    if not ch:
        print("Channel 1 not found in DB")
        return

    print(f"Force Starting Channel 1 (Slot: prime_time)...")
    await client.start_workflow(
        MasterBulletinWorkflow.run, 
        {"channel_id": 1, "stream_key": ch.youtube_stream_key, "file_prefix": "prime_time"}, 
        id="manual-start-ch1-final", 
        task_queue="news-task-queue"
    )
    print("Workflow started successfully.")

if __name__ == "__main__":
    asyncio.run(run())
