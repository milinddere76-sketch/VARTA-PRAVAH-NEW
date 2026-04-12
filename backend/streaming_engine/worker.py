import os
import sys

# Fix imports for Docker/Production/Local
# Ensure the 'backend' root is in sys.path before importing local modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import asyncio
import time
from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from .workflows import NewsProductionWorkflow, StopStreamWorkflow
from .activities import (
    fetch_news_activity,
    generate_script_activity,
    generate_headlines_activity,
    generate_closing_activity,
    generate_audio_activity,
    generate_news_video_activity,
    synclabs_lip_sync_activity,
    check_sync_labs_status_activity,
    upload_to_s3_activity,
    start_stream_activity,
    ensure_promo_video_activity,
    ensure_premium_promo_activity,
    stop_stream_activity,
    check_scheduled_ads_activity,
    cleanup_old_videos_activity
)

from database import get_session_local
from models import Channel, User, Anchor
from sqlalchemy.orm import Session
import temporal_utils


# ================= DB SEED ================= #

async def seed_database():
    """
    Ensures the default user, 2 anchors (female + male), and default channel
    all exist. Returns (anchor_female_id, anchor_male_id).
    """
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    anchor_female_id = None
    anchor_male_id = None
    try:
        # --- Default System User ---
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(id=1, email="system@vartapravah.ai", hashed_password="seed_password")
            db.add(user)
            db.commit()

        # --- Female Anchor (Priya) ---
        female = db.query(Anchor).filter(Anchor.gender == "female", Anchor.is_active == True).first()
        if not female:
            female = Anchor(
                name="Priya Desai", 
                gender="female", 
                portrait_url="assets/female_anchor.png",
                description="Professional female news anchor", 
                is_active=True
            )
            db.add(female)
            db.commit()
            db.refresh(female)
        anchor_female_id = female.id

        # --- Male Anchor (Arjun) ---
        male = db.query(Anchor).filter(Anchor.gender == "male", Anchor.is_active == True).first()
        if not male:
            male = Anchor(
                name="Arjun Sharma", 
                gender="male", 
                portrait_url="assets/male_anchor.png",
                description="Professional male news anchor", 
                is_active=True
            )
            db.add(male)
            db.commit()
            db.refresh(male)
        anchor_male_id = male.id

        # --- Channel 1 ---
        channel1 = db.query(Channel).filter(Channel.id == 1).first()
        if not channel1:
            key1 = os.getenv("YOUTUBE_STREAM_KEY", "")
            channel1 = Channel(id=1, name="Varta Pravah Channel 1", language="Marathi", youtube_stream_key=key1, owner_id=1, preferred_anchor_id=anchor_female_id)
            db.add(channel1)
            db.commit()

        # --- Channel 2 ---
        channel2 = db.query(Channel).filter(Channel.id == 2).first()
        if not channel2:
            key2 = "9efm-d8gq-mmma-9y1b-7sez"
            channel2 = Channel(id=2, name="Varta Pravah Channel 2", language="Marathi", youtube_stream_key=key2, owner_id=1, preferred_anchor_id=anchor_male_id)
            db.add(channel2)
            db.commit()

        print(f" DB Seed complete  Female anchor id: {anchor_female_id}, Male anchor id: {anchor_male_id}")
        return anchor_female_id, anchor_male_id

    except Exception as e:
        print(f" DB Seed error: {e}")
        return None, None
    finally:
        db.close()


# ================= AUTOSTART ================= #

async def trigger_auto_start(client: Client):
    anchor_female_id, anchor_male_id = await seed_database()

    channel_id = int(os.getenv("AUTO_START_CHANNEL_ID", "1"))
    language = os.getenv("DEFAULT_LANGUAGE", "Marathi").strip()
    stream_key = os.getenv("YOUTUBE_STREAM_KEY", "")

    if not stream_key:
        print(" Missing YOUTUBE_STREAM_KEY  cannot start stream")
        return

    workflow_id = f"news-production-{channel_id}"

    # Wait for Temporal to be ready
    print(f" Connecting to Temporal to start Channel {channel_id} workflow...")
    for i in range(10):
        try:
            await client.get_workflow_handle(workflow_id).describe()
            break
        except Exception:
            if i == 9: break 
            print(f" ⏳ Waiting for Temporal service... (Attempt {i+1}/10)")
            await asyncio.sleep(5)

    # Terminate any existing workflow (running or stuck) and start fresh.
    try:
        handle = client.get_workflow_handle(workflow_id)
        desc = await handle.describe()
        status = desc.status.name
        print(f" Found existing workflow '{workflow_id}' with status: {status}")
        try:
            await handle.terminate(reason="Redeployment - starting fresh")
            print(f" Terminated previous workflow ({status})")
            await asyncio.sleep(5)
        except: pass
    except: pass

    # Wait for DB seed to be ready (ensure Channel 2 exists)
    print(f" Checking database for Channel {channel_id}...")
    for i in range(12):
        db = next(database.get_db())
        channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
        if channel:
            print(f" ✅ Channel {channel_id} found in DB.")
            break
        print(f" ⏳ Waiting for Database Seed... (Attempt {i+1}/12)")
        await asyncio.sleep(5)

    # Start workflow
    try:
        await client.start_workflow(
            NewsProductionWorkflow.run,
            {
                "channel_id": channel_id,
                "language": language,
                "stream_key": stream_key,
                "anchor_ids": [anchor_female_id, anchor_male_id]
            },
            id=workflow_id,
            task_queue="news-task-queue"
        )
        print(" Varta Pravah workflow started  connecting to YouTube immediately")

    except Exception as e:
        if "already started" in str(e).lower():
            print(" Workflow already running (race condition caught)")
        else:
            print(f" Workflow start issue: {e}")


# ================= MAIN ================= #

async def main():
    from dotenv import load_dotenv
    load_dotenv()

    # Start heartbeat in background
    def write_status(msg):
        try:
            os.makedirs("/app/videos", exist_ok=True)
            with open("/app/videos/worker_status.txt", "w") as f:
                f.write(f"{time.ctime()}: {msg}")
        except: pass

    write_status("Connecting to Temporal (Retrying for 5 mins)...")
    client = None
    for i in range(60):
        try:
            client = await temporal_utils.get_temporal_client()
            if client:
                write_status("Connected to Temporal - Registering Activities")
                print(" Connected to Temporal")
                break
        except Exception as e:
            write_status(f"Connect Retry {i+1}/60: {str(e)}")
            await asyncio.sleep(5)

    if not client:
        write_status("CRITICAL: Failed to connect to Temporal after 12 retries")
        raise RuntimeError(" Cannot connect to Temporal")

    # Start workflow in background 
    asyncio.create_task(trigger_auto_start(client))
    write_status("Worker Running - Polling news-task-queue")

    channel_id_env = os.getenv("AUTO_START_CHANNEL_ID", "1")
    worker = Worker(
        client,
        task_queue="news-task-queue",
        workflows=[NewsProductionWorkflow, StopStreamWorkflow],
        activities=[
            fetch_news_activity,
            generate_script_activity,
            generate_headlines_activity,
            generate_closing_activity,
            generate_audio_activity,
            generate_news_video_activity,
            synclabs_lip_sync_activity,
            check_sync_labs_status_activity,
            upload_to_s3_activity,
            start_stream_activity,
            ensure_promo_video_activity,
            ensure_premium_promo_activity,
            stop_stream_activity,
            check_scheduled_ads_activity,
            cleanup_old_videos_activity
        ],
        identity=f"Worker-Ch{channel_id_env}",
        workflow_runner=UnsandboxedWorkflowRunner()
    )

    print(" Worker started and polling")

    try:
        await worker.run()
    except Exception as e:
        print(f" Worker crashed: {e}")
        raise


# ================= ENTRY ================= #

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f" Fatal error: {e}")