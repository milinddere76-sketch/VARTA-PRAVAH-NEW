import asyncio
import os
import sys
from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from .workflows import NewsProductionWorkflow
from .activities import (
    fetch_news_activity,
    generate_script_activity,
    synclabs_lip_sync_activity,
    check_sync_labs_status_activity,
    upload_to_s3_activity,
    start_stream_activity,
    ensure_promo_video_activity
)

# Hardened Imports for Docker Subdirectory execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import Channel, User
from sqlalchemy.orm import Session

async def seed_database():
    """Integrated Seeder: Ensure Channel 1 exists immediately on deployment."""
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
    await seed_database()
    channel_id = os.getenv("AUTO_START_CHANNEL_ID", "1")
    language = os.getenv("DEFAULT_LANGUAGE", "mr")
    stream_key = os.getenv("YOUTUBE_STREAM_KEY", "")
    workflow_id = f"news-production-{channel_id}"

    if not stream_key: return

    try:
        handle = client.get_workflow_handle(workflow_id)
        desc = await handle.describe()
        if desc.status.name == "RUNNING": return
    except Exception: pass

    try:
        await client.start_workflow(
            NewsProductionWorkflow.run,
            {"channel_id": int(channel_id), "language": language, "stream_key": stream_key},
            id=workflow_id, task_queue="news-task-queue"
        )
    except Exception as e: print(f"Auto-trigger error: {e}")

async def main():
    from dotenv import load_dotenv
    load_dotenv()
    
    temporal_host = os.getenv("TEMPORAL_ADDRESS") or "temporal:7233"
    client = None
    
    for i in range(24):
        try:
            client = await Client.connect(temporal_host)
            print(f"Connected to Temporal on {temporal_host}!")
            break
        except Exception:
            print(f"Syncing with News Engine... ({i+1}/24)")
            await asyncio.sleep(10)
    
    if not client: return

    asyncio.create_task(trigger_auto_start(client))
    
    worker = Worker(
        client, task_queue="news-task-queue",
        workflows=[NewsProductionWorkflow],
        activities=[
            fetch_news_activity, generate_script_activity,
            synclabs_lip_sync_activity, check_sync_labs_status_activity,
            upload_to_s3_activity, start_stream_activity, ensure_promo_video_activity
        ],
        workflow_runner=UnsandboxedWorkflowRunner()
    )
    print("News Worker Online.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
