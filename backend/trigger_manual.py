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

async def trigger_news(channel_id: int):
    print(f"--- [MANUAL TRIGGER] Starting News Generation for Channel {channel_id} ---")
    
    # 1. Connect to Temporal
    try:
        client = await temporal_utils.get_temporal_client()
    except Exception as e:
        print(f"❌ Could not connect to Temporal: {e}")
        return

    # 2. Get Channel Info from DB
    db = next(database.get_db())
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel:
        print(f"❌ Channel {channel_id} not found in database.")
        return

    if not channel.youtube_stream_key:
        print(f"❌ Channel {channel_id} has no stream key set.")
        return

    # 3. Get Anchor IDs for seeding (optional but good for consistency)
    anchors = db.query(models.Anchor).filter(models.Anchor.is_active == True).all()
    anchor_ids = [a.id for a in anchors]

    # 4. Start Workflow
    workflow_id = f"news-production-{channel_id}"
    input_data = {
        "channel_id": channel_id,
        "language": channel.language,
        "stream_key": channel.youtube_stream_key,
        "anchor_ids": anchor_ids
    }

    try:
        # Terminate existing if any
        try:
            handle = client.get_workflow_handle(workflow_id)
            await handle.terminate(reason="Manual trigger restart")
            print(f"  Terminated existing workflow {workflow_id}")
            await asyncio.sleep(2)
        except: pass

        handle = await client.start_workflow(
            "NewsProductionWorkflow",
            input_data,
            id=workflow_id,
            task_queue="news-task-queue"
        )
        print(f"✅ Workflow started successfully!")
        print(f"   Workflow ID: {handle.id}")
        print(f"   Run ID: {handle.result_run_id}")
        
        # Update DB status
        channel.is_streaming = True
        db.commit()

    except Exception as e:
        print(f"❌ Error starting workflow: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trigger_manual.py <channel_id>")
        sys.exit(1)
    
    cid = int(sys.argv[1])
    asyncio.run(trigger_news(cid))
