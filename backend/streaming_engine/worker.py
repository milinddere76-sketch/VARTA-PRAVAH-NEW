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
from .workflows import NewsProductionWorkflow, StopStreamWorkflow, MasterBulletinWorkflow, BreakingNewsWorkflow

import database
import models
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
    merge_videos_activity,
    stitch_bulletin_activity,
    find_latest_bulletin_activity
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
            key2 = os.getenv("YOUTUBE_STREAM_KEY_CH2", "9efm-d8gq-mmma-9y1b-7sez")
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
    from .scheduler import setup_schedules

    # Determine if we should start all channels or just one
    auto_all = os.getenv("AUTO_START_ALL_CHANNELS", "False").lower() == "true"
    auto_cid = int(os.getenv("AUTO_START_CHANNEL_ID", "1"))
    
    db = next(database.get_db())
    if auto_all:
        channels = db.query(models.Channel).all()
    else:
        channels = db.query(models.Channel).filter(models.Channel.id == auto_cid).all()
    db.close()

    for channel in channels:
        channel_id = channel.id
        stream_key = channel.youtube_stream_key
        
        if not stream_key: continue

        # 1. Setup Schedules (Daily Bulletins + Breaking News)
        await setup_schedules(
            client, 
            channel_id, 
            stream_key, 
            [anchor_female_id, anchor_male_id]
        )
        
        # 2. Start initial Promo loop immediately via a one-off workflow
        # so the channel isn't empty while waiting for the first scheduled bulletin
        try:
            await client.start_workflow(
                start_stream_activity,
                {"channel_id": channel_id, "stream_key": stream_key, "video_url": f"videos/promo_ch{channel_id}.mp4", "is_promo": True},
                id=f"initial-promo-ch{channel_id}",
                task_queue="news-task-queue"
            )
            print(f"✅ Initial Promo triggered for CH{channel_id}")
        except: pass






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
    # Retry connection to Temporal with progressive backoff
    client = None
    for i in range(30):
        try:
            client = await temporal_utils.get_temporal_client()
            if client:
                write_status("Connected to Temporal - Registering Activities")
                print(" Connected to Temporal")
                break
        except Exception as e:
            # Progressive delay: start fast, then slow down to give server breathing room
            delay = min(2 + (i // 2), 15) 
            write_status(f"Connect Retry {i+1}/30 (Wait {delay}s): {str(e)}")
            await asyncio.sleep(delay)

    if not client:
        write_status("CRITICAL: Failed to connect to Temporal after 30 retries")
        raise RuntimeError(" Cannot connect to Temporal")

    # Start workflow in background 
    asyncio.create_task(trigger_auto_start(client))
    write_status("Worker Running - Polling news-task-queue")

    channel_id_env = os.getenv("AUTO_START_CHANNEL_ID", "1")
    worker = Worker(
        client,
        task_queue="news-task-queue",
        workflows=[NewsProductionWorkflow, StopStreamWorkflow, MasterBulletinWorkflow, BreakingNewsWorkflow],
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
            merge_videos_activity,
            stitch_bulletin_activity,
            find_latest_bulletin_activity
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