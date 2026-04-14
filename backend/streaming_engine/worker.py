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

async def trigger_auto_start(client: Client):
    await seed_database()
    channel_id = int(os.getenv("AUTO_START_CHANNEL_ID", "1"))
    language = "Marathi"
    stream_key = os.getenv("YOUTUBE_STREAM_KEY")
    if not stream_key:
        print("❌ CRITICAL: YOUTUBE_STREAM_KEY not found in environment!")
        return

    # Start Main Production with static ID for signaling
    try:
        await client.start_workflow(
            NewsProductionWorkflow.run,
            channel_id,
            stream_key,
            language,
            id="news-production-auto",
            task_queue="news-task-queue-v2"
        )
        print("🚀 News Production Workflow Started (Auto-Mode)")
    except Exception as e:
        print(f"⚠️ Production Workflow Start Error: {e}")

    # Start Breaking News Monitor
    try:
        await client.start_workflow(
            CheckBreakingNewsWorkflow.run,
            id="breaking-news-monitor",
            task_queue="news-task-queue-v2"
        )
        print("👀 Breaking News Monitor Started")
    except Exception as e:
        print(f"⚠️ Monitor Workflow Start Error: {e}")

# ================= MAIN ================= #

async def main():
    write_status = lambda m: None # Simplified
    client = await temporal_utils.get_temporal_client()
    
    # Instant Connect (Standby)
    abs_promo = "/app/videos/promo.mp4"
    if not os.path.exists(abs_promo):
        subprocess.run([sys.executable, "/app/create_premium_promo.py", abs_promo])
    
    try:
        await start_stream_activity({
            "channel_id": 1,
            "stream_key": os.getenv("YOUTUBE_STREAM_KEY", "key"),
            "video_url": abs_promo
        })
    except: pass

    asyncio.create_task(trigger_auto_start(client))

    worker = Worker(
        client,
        task_queue="news-task-queue-v2",
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
            check_breaking_news_activity
        ],
        workflow_runner=UnsandboxedWorkflowRunner()
    )
    print("✨ Worker Started - 24x7 Schedule Live")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())