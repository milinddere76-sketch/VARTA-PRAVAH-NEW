import asyncio
import os
import sys
from datetime import datetime
import zoneinfo

# Add current dir to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import temporal_utils
from streaming_engine.workflows import NewsBatchWorkflow, MasterBulletinWorkflow
from database import get_session_local
import models

async def bootstrap():
    print("--- [BOOTSTRAP] Starting AI News Production ---")
    client = await temporal_utils.get_temporal_client()
    
    # 1. Get IDs
    db = get_session_local()()
    channel = db.query(models.Channel).first()
    female_anchor = db.query(models.Anchor).filter(models.Anchor.gender == "female").first()
    male_anchor = db.query(models.Anchor).filter(models.Anchor.gender == "male").first()
    db.close()
    
    if not channel or not female_anchor or not male_anchor:
        print("❌ Error: Missing DB initialization (run worker first to seed)")
        return

    channel_id = channel.id
    stream_key = channel.youtube_stream_key
    anchor_ids = [female_anchor.id, male_anchor.id]

    # 2. Trigger News Batch Generation (Evening Cycle)
    print(f"--- [BATCH] Triggering NewsBatchWorkflow (Evening Cycle) for CH{channel_id}...")
    batch_handle = await client.start_workflow(
        NewsBatchWorkflow.run,
        {"channel_id": channel_id, "cycle": "Evening", "anchor_ids": anchor_ids},
        id=f"manual-batch-{datetime.now().strftime('%Y%m%d-%H%M')}",
        task_queue="news-task-queue"
    )
    
    print(f"--- [WAIT] Waiting for batch generation to complete (approx 10-20 mins) ---")
    print(f"--- [INFO] You can monitor progress at http://localhost:8088 ---")
    
    # In a real bootstrap, we might wait. For this script, we'll start the slot check.
    # Note: If files aren't ready yet, the Broadcaster will fallback to promo.
    
    # 3. Trigger MasterBulletinBroadcaster for Current Slot
    # Since it's ~21:00, we use prime_time or evening_headlines
    print(f"--- [SLOT] Triggering Slot Broadcaster (prefix: prime_time) for CH{channel_id}...")
    await client.start_workflow(
        MasterBulletinWorkflow.run,
        {"channel_id": channel_id, "stream_key": stream_key, "file_prefix": "prime_time"},
        id=f"manual-slot-{datetime.now().strftime('%H%M')}",
        task_queue="news-task-queue"
    )

    print(f"--- [DONE] Bootstrap command sent. News is being generated and channel will go live shortly.")


if __name__ == "__main__":
    asyncio.run(bootstrap())
