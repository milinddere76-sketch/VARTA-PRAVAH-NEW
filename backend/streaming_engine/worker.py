import os
import sys

# Fix imports for Docker/Production/Local
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import asyncio
import time
import subprocess
from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from .workflows import NewsProductionWorkflow, StopStreamWorkflow, CheckBreakingNewsWorkflow
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
    merge_videos_activity,
    ensure_promo_video_activity,
    ensure_premium_promo_activity,
    stop_stream_activity,
    check_scheduled_ads_activity,
    cleanup_old_videos_activity,
    get_channel_anchor_activity,
    check_breaking_news_activity
)
from activities.anchor_activity import get_anchor_activity
from activities.breaking_player import play_breaking_activity

from database import get_session_local
from models import Channel, User, Anchor
from sqlalchemy.orm import Session
import temporal_utils


# ================= DB SEED ================= #

async def seed_database():
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    try:
        # Female Anchor (Priya)
        female = db.query(Anchor).filter(Anchor.gender == "female").first()
        if not female:
            db.add(Anchor(name="Priya Desai", gender="female", portrait_url="assets/female_anchor.png", is_active=True))
            db.commit()

        # Male Anchor (Arjun)
        male = db.query(Anchor).filter(Anchor.gender == "male").first()
        if not male:
            db.add(Anchor(name="Arjun Sharma", gender="male", portrait_url="assets/male_anchor.png", is_active=True))
            db.commit()

        # Channel
        channel = db.query(Channel).filter(Channel.id == 1).first()
        if not channel:
            db.add(Channel(id=1, name="Varta Pravah Live", language="Marathi", youtube_stream_key=os.getenv("YOUTUBE_STREAM_KEY", "key"), owner_id=1))
            db.commit()
    finally:
        db.close()

# ================= AUTOSTART ================= #

async def launch_production(client, channel_id, stream_key, language):
    """Isolated production launcher to prevent cross-failure."""
    print(f"🎬 [AUTO-START] Attempting to launch Production Workflow for Channel {channel_id}...")
    try:
        await client.start_workflow(
            NewsProductionWorkflow.run,
            args=[channel_id, stream_key, language],
            id="news-production-auto",
            task_queue="news-task-queue-v4"
        )
        print("✅ [AUTO-START] News Production Workflow ACTIVE.")
    except Exception as e:
        print(f"⚠️ [AUTO-START] Production already running or failed: {e}")

async def launch_monitor(client):
    """Isolated monitor launcher."""
    print("🎬 [AUTO-START] Attempting to launch Breaking News Monitor...")
    try:
        await client.start_workflow(
            CheckBreakingNewsWorkflow.run,
            id="breaking-news-monitor",
            task_queue="news-task-queue-v4"
        )
        print("✅ [AUTO-START] Breaking News Monitor ACTIVE.")
    except Exception as e:
        print(f"⚠️ [AUTO-START] Monitor already running or failed: {e}")

async def main():
    # 0. IMMEDIATE YOUTUBE HANDSHAKE (No blocking)
    s_key = os.getenv("YOUTUBE_STREAM_KEY")
    if s_key:
        from streaming_engine.activities import start_stream_activity
        async def delayed_standby():
            # Wait up to 30s for the file to appear (Zero-Gap stability)
            for _ in range(6):
                if os.path.exists("/app/videos/promo.mp4"):
                    await start_stream_activity({
                        "channel_id": 1,
                        "stream_key": s_key,
                        "video_url": "/app/videos/promo.mp4"
                    })
                    print("🚀 [INGEST] Instant Standby Triggered!")
                    return
                print("⏳ [INGEST] Waiting for promo.mp4 to appear...")
                await asyncio.sleep(5)
            print("⚠️ [INGEST] Instant Standby timed out - asset missing.")

        asyncio.create_task(delayed_standby())

    # 1. Database & Asset Prep
    try:
        await seed_database()
        print("📂 [INIT] Database seed complete.")
    except: pass

    # 2. Connect to Brain (Optional/Retry)
    try:
        client = await temporal_utils.get_temporal_client()
    except Exception as e:
        print(f"⚠️ [SYSTEM] Brain still offline, remaining in autonomous standby: {e}")
        # Wait forever in standby loop
        while True: await asyncio.sleep(3600)

    # 3. Isolated Background Launches
    print("⏳ [BOOT] Staggering production start (15s) for RAM stability...")
    await asyncio.sleep(15)
    
    channel_id = int(os.getenv("AUTO_START_CHANNEL_ID", "1"))
    language = "Marathi"
    
    asyncio.create_task(launch_production(client, channel_id, s_key, language))
    asyncio.create_task(launch_monitor(client))

    # 4. Start Worker (Indestructible Execution)
    worker = Worker(
        client,
        task_queue="news-task-queue-v4",
        workflows=[NewsProductionWorkflow, StopStreamWorkflow, CheckBreakingNewsWorkflow],
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
            merge_videos_activity,
            ensure_promo_video_activity,
            ensure_premium_promo_activity,
            stop_stream_activity,
            check_scheduled_ads_activity,
            cleanup_old_videos_activity,
            get_channel_anchor_activity,
            check_breaking_news_activity,
            get_anchor_activity,
            play_breaking_activity
        ],
        workflow_runner=UnsandboxedWorkflowRunner()
    )
    
    print("🚀 [SYSTEM] Worker running forever on news-task-queue-v4")
    while True:
        try:
            await worker.run()
        except Exception as e:
            print(f"❌ [CRITICAL] Worker connection lost: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    import sys
    # Force output flushing for Docker logging
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main())