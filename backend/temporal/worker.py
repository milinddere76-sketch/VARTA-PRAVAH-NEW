import asyncio
import os
import sys
import time
from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from .workflows import NewsProductionWorkflow, StopStreamWorkflow
from .activities import (
    fetch_news_activity,
    generate_script_activity,
    generate_audio_activity,
    generate_news_video_activity,
    synclabs_lip_sync_activity,
    check_sync_labs_status_activity,
    upload_to_s3_activity,
    start_stream_activity,
    ensure_promo_video_activity,
    stop_stream_activity,
    check_scheduled_ads_activity,
    cleanup_old_videos_activity
)

# Fix imports for Docker
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_session_local
from models import Channel, User
from sqlalchemy.orm import Session
import temporal_utils


# ================= DB SEED ================= #

async def seed_database():
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(
                id=1,
                email="system@vartapravah.ai",
                hashed_password="seed_password"
            )
            db.add(user)
            db.commit()

        channel = db.query(Channel).filter(Channel.id == 1).first()
        if not channel:
            stream_key = os.getenv("YOUTUBE_STREAM_KEY", "")
            channel = Channel(
                id=1,
                name="Varta Pravah Live",
                language="Marathi",
                youtube_stream_key=stream_key,
                owner_id=1
            )
            db.add(channel)
            db.commit()

        print("✅ DB Seed completed")

    except Exception as e:
        print(f"⚠️ DB Seed skipped: {e}")

    finally:
        db.close()


# ================= AUTOSTART ================= #

async def trigger_auto_start(client: Client):
    await seed_database()

    channel_id = int(os.getenv("AUTO_START_CHANNEL_ID", "1"))
    language = os.getenv("DEFAULT_LANGUAGE", "Marathi").strip()
    stream_key = os.getenv("YOUTUBE_STREAM_KEY", "")

    if not stream_key:
        print("⚠️ Missing YOUTUBE_STREAM_KEY")
        return

    workflow_id = f"news-production-{channel_id}"

    # Check existing workflow
    try:
        handle = client.get_workflow_handle(workflow_id)
        desc = await handle.describe()
        if desc.status.name == "RUNNING":
            print("✅ Already running")
            return
    except Exception:
        pass

    # Start workflow
    try:
        await client.start_workflow(
            NewsProductionWorkflow.run,
            {
                "channel_id": channel_id,
                "language": language,
                "stream_key": stream_key
            },
            id=workflow_id,
            task_queue="news-task-queue"
        )
        print("🚀 Workflow started")

    except Exception as e:
        print(f"⚠️ Workflow start issue: {e}")


# ================= MAIN ================= #

async def main():
    from dotenv import load_dotenv
    load_dotenv()

    # Retry connect to Temporal
    client = None
    for i in range(10):
        try:
            client = await temporal_utils.get_temporal_client()
            if client:
                print("✅ Connected to Temporal")
                break
        except Exception as e:
            print(f"Retry Temporal connect {i+1}/10...")
            await asyncio.sleep(5)

    if not client:
        raise RuntimeError("❌ Cannot connect to Temporal")

    # Start auto workflow in background
    asyncio.create_task(trigger_auto_start(client))

    worker = Worker(
        client,
        task_queue="news-task-queue",
        workflows=[NewsProductionWorkflow, StopStreamWorkflow],
        activities=[
            fetch_news_activity,
            generate_script_activity,
            generate_audio_activity,
            generate_news_video_activity,
            synclabs_lip_sync_activity,
            check_sync_labs_status_activity,
            upload_to_s3_activity,
            start_stream_activity,
            ensure_promo_video_activity,
            stop_stream_activity,
            check_scheduled_ads_activity,
            cleanup_old_videos_activity
        ],
        workflow_runner=UnsandboxedWorkflowRunner()
    )

    print("🚀 Worker started")

    try:
        await worker.run()
    except Exception as e:
        print(f"❌ Worker crashed: {e}")
        raise


# ================= ENTRY ================= #

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Fatal error: {e}")