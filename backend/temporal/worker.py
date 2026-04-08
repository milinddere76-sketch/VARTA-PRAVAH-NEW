import asyncio
import os
import sys
from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from .workflows import NewsProductionWorkflow, StopStreamWorkflow
from .activities import (
    fetch_news_activity,
    generate_script_activity,
    synclabs_lip_sync_activity,
    check_sync_labs_status_activity,
    upload_to_s3_activity,
    start_stream_activity,
    ensure_promo_video_activity,
    stop_stream_activity,
    check_scheduled_ads_activity,
    cleanup_old_videos_activity
)

# Hardened Imports for Docker Subdirectory execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_session_local
from models import Channel, User
from sqlalchemy.orm import Session
import temporal_utils

async def seed_database():
    """Integrated Seeder: Ensure Channel 1 exists immediately on deployment."""
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    try:
        # 1. System User
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(id=1, email="system@vartapravah.ai", hashed_password="seed_password_not_used")
            db.add(user)
            db.commit()

        # 2. Channel 1
        channel = db.query(Channel).filter(Channel.id == 1).first()
        if not channel:
            stream_key = os.getenv("YOUTUBE_STREAM_KEY", "qcu7-xesd-m4sv-9zvv-e335")
            channel = Channel(
                id=1, name="Varta Pravah Live", language="Marathi", 
                youtube_stream_key=stream_key, owner_id=1
            )
            db.add(channel)
            db.commit()
            print(f"BOOTSTRAP: Channel 1 seeded with key {stream_key[:4]}****")
    except Exception as e:
        print(f"BOOTSTRAP: Seeding deferred (DB warming up...): {e}")
    finally:
        db.close()

async def trigger_auto_start(client: Client):
    """🚀 Autonomous Engine Ignition: Automatically starts news production on boot."""
    await seed_database()
    channel_id = os.getenv("AUTO_START_CHANNEL_ID", "1")
    language = os.getenv("DEFAULT_LANGUAGE", " Marathi").strip()
    stream_key = os.getenv("YOUTUBE_STREAM_KEY", "")
    workflow_id = f"news-production-{channel_id}"

    if not stream_key:
        print("🛰️ AUTOPILOT: Waiting for YOUTUBE_STREAM_KEY to be configured...")
        return

    # 🔄 Attempt to start the workflow with retries
    for attempt in range(5):
        try:
            print(f"🛰️ AUTOPILOT: Checking for active broadcast (Attempt {attempt+1}/5)...")
            handle = client.get_workflow_handle(workflow_id)
            desc = await handle.describe()
            if desc.status.name == "RUNNING":
                print(f"✅ AUTOPILOT: Channel {channel_id} is already LIVE. Resuming monitoring.")
                return
        except Exception:
            # Workflow doesn't exist yet, proceeding to start
            break
        await asyncio.sleep(5)

    try:
        print(f"🚀 AUTOPILOT: Launching news production workflow for Channel {channel_id}...")
        await client.start_workflow(
            NewsProductionWorkflow.run,
            {"channel_id": int(channel_id), "language": language, "stream_key": stream_key},
            id=workflow_id, task_queue="news-task-queue"
        )
        print("✅ AUTOPILOT: Workflow launched successfully!")
    except Exception as e:
        print(f"❌ AUTOPILOT ERROR: {e}")

async def main():
    from dotenv import load_dotenv
    load_dotenv()
    
    client = await temporal_utils.get_temporal_client()
    
    if not client: return

    asyncio.create_task(trigger_auto_start(client))
    
    worker = Worker(
        client, task_queue="news-task-queue",
        workflows=[NewsProductionWorkflow, StopStreamWorkflow],
        activities=[
            fetch_news_activity, generate_script_activity,
            synclabs_lip_sync_activity, check_sync_labs_status_activity,
            upload_to_s3_activity, start_stream_activity, ensure_promo_video_activity,
            stop_stream_activity, check_scheduled_ads_activity,
            cleanup_old_videos_activity
        ],
        workflow_runner=UnsandboxedWorkflowRunner()
    )
    print("News Worker Online.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
