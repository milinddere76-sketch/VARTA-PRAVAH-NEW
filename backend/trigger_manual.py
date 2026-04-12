import asyncio
import sys
import os
from temporalio.client import Client

# Add backend to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import temporal_utils
import database
import models

async def trigger_news(channel_id: int, b_type: str = "Regular"):
    print(f"--- [MANUAL TRIGGER] Starting {b_type} Bulletin for Channel {channel_id} ---")
    
    # 1. Connect to Temporal
    try:
        client = await temporal_utils.get_temporal_client()
    except Exception as e:
        print(f"ERROR: Could not connect to Temporal: {e}")
        return

    # 2. Get Channel Info from DB
    db = next(database.get_db())
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel:
        print(f"ERROR: Channel {channel_id} not found in database.")
        db.close()
        return

    if not channel.youtube_stream_key:
        print(f"ERROR: Channel {channel_id} has no stream key set.")
        db.close()
        return

    # 3. Get Anchor IDs
    anchors = db.query(models.Anchor).filter(models.Anchor.is_active == True).all()
    anchor_ids = [a.id for a in anchors]
    db.close()

    # 4. Start Workflow
    workflow_id = f"manual-bulletin-{b_type}-{channel_id}"
    input_data = {
        "channel_id": channel_id,
        "language": channel.language,
        "stream_key": channel.youtube_stream_key,
        "anchor_ids": anchor_ids,
        "bulletin_type": b_type
    }

    try:
        # Terminate existing if any
        try:
            handle = client.get_workflow_handle(workflow_id)
            await handle.terminate(reason="Manual trigger override")
            print(f"   Terminated existing stuck workflow {workflow_id}")
            await asyncio.sleep(2)
        except: pass

        handle = await client.start_workflow(
            "MasterBulletinWorkflow",
            input_data,
            id=workflow_id,
            task_queue="news-task-queue"
        )

        print(f"SUCCESS: Master Bulletin started successfully!")
        print(f"   Workflow ID: {handle.id}")
        
    except Exception as e:
        print(f"ERROR: starting workflow: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("channel_id", type=int)
    parser.add_argument("--type", default="Regular", help="Bulletin type (Morning, etc.)")
    args = parser.parse_args()
    
    asyncio.run(trigger_news(args.channel_id, args.type))

