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
    ensure_premium_promo_activity,
    stop_stream_activity,
    check_scheduled_ads_activity,
    cleanup_old_videos_activity
)

# Fix imports for Docker/Production
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

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
            female = Anchor(name="Priya Desai", gender="female", description="Professional female news anchor", is_active=True)
            db.add(female)
            db.commit()
            db.refresh(female)
        anchor_female_id = female.id

        # --- Male Anchor (Arjun) ---
        male = db.query(Anchor).filter(Anchor.gender == "male", Anchor.is_active == True).first()
        if not male:
            male = Anchor(name="Arjun Sharma", gender="male", description="Professional male news anchor", is_active=True)
            db.add(male)
            db.commit()
            db.refresh(male)
        anchor_male_id = male.id

        # --- Default Channel ---
        channel = db.query(Channel).filter(Channel.id == 1).first()
        if not channel:
            stream_key = os.getenv("YOUTUBE_STREAM_KEY", "")
            channel = Channel(
                id=1,
                name="Varta Pravah Live",
                language="Marathi",
                youtube_stream_key=stream_key,
                owner_id=1,
                preferred_anchor_id=anchor_female_id
            )
            db.add(channel)
            db.commit()
        else:
            # Always keep stream key in sync with env var
            env_key = os.getenv("YOUTUBE_STREAM_KEY", "")
            if env_key and channel.youtube_stream_key != env_key:
                channel.youtube_stream_key = env_key
                db.commit()

        print(f"✅ DB Seed complete — Female anchor id: {anchor_female_id}, Male anchor id: {anchor_male_id}")
        return anchor_female_id, anchor_male_id

    except Exception as e:
        print(f"⚠️ DB Seed error: {e}")
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
        print("⚠️ Missing YOUTUBE_STREAM_KEY — cannot start stream")
        return

    workflow_id = f"news-production-{channel_id}"

    # Terminate any existing workflow (running or stuck) and start fresh.
    # A healthy deployment always needs a clean workflow start.
    try:
        handle = client.get_workflow_handle(workflow_id)
        desc = await handle.describe()
        status = desc.status.name  # e.g. RUNNING, FAILED, TIMED_OUT, COMPLETED
        print(f"🔍 Found existing workflow '{workflow_id}' with status: {status}")
        # Always terminate so we start fresh with new code/settings
        try:
            await handle.terminate(reason="Redeployment — starting fresh")
            print(f"🛑 Terminated previous workflow ({status})")
            await asyncio.sleep(3)   # give Temporal time to close it
        except Exception as term_err:
            print(f"⚠️  Could not terminate workflow (may be already closed): {term_err}")
    except Exception:
        # Workflow doesn't exist yet — fresh start
        print(f"ℹ️  No existing workflow '{workflow_id}' — will create fresh")

    # Start workflow — pass both anchor IDs so it alternates them
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
        print("🚀 Varta Pravah workflow started — connecting to YouTube immediately")

    except Exception as e:
        if "already started" in str(e).lower():
            print("✅ Workflow already running (race condition caught)")
        else:
            print(f"⚠️ Workflow start issue: {e}")


# ================= MAIN ================= #

async def main():
    from dotenv import load_dotenv
    load_dotenv()

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

    # Start workflow in background (non-blocking so worker registers immediately)
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
            ensure_premium_promo_activity,
            stop_stream_activity,
            check_scheduled_ads_activity,
            cleanup_old_videos_activity
        ],
        workflow_runner=UnsandboxedWorkflowRunner()
    )

    print("🚀 Worker started and polling")

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