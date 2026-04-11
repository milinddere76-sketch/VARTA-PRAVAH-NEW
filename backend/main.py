from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
import os
from sqlalchemy.orm import Session
from temporalio.client import Client
import database, models, schemas, temporal_utils
from datetime import timedelta
from streaming_engine.workflows import NewsProductionWorkflow, StopStreamWorkflow

from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and seed default user
    database.init_db()
    db = next(database.get_db())
    if not db.query(models.User).filter(models.User.id == 1).first():
        default_user = models.User(
            id=1,
            email="admin@vartapravah.com",
            hashed_password="hashed_password",
            full_name="Admin User"
        )
        db.add(default_user)
        db.commit()
    db.close()
    yield
    # Shutdown logic (optional)

app = FastAPI(title="VartaPravah API", lifespan=lifespan)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "VartaPravah API Engine Online", "version": "1.0.0"}

import subprocess
import socket

@app.get("/debug/health")
async def server_health_check():
    checks = {}
    try:
        with socket.create_connection(("a.rtmp.youtube.com", 1935), timeout=5):
            checks["youtube_rtmp_1935"] = "REACHABLE"
    except Exception as e:
        checks["youtube_rtmp_1935"] = f"BLOCKED: {str(e)}"
    
    # Check if promo exists
    checks["promo_exists"] = os.path.exists("/app/videos/promo.mp4")
    
    # Check for zombie ffmpeg processes
    try:
        ps = subprocess.run(["pgrep", "-f", "ffmpeg"], capture_output=True, text=True)
        checks["active_ffmpeg_pids"] = ps.stdout.strip().split("\n") if ps.stdout.strip() else []
    except:
        checks["active_ffmpeg_pids"] = "pgrep not available"

    return checks


async def get_temporal_client():
    return await temporal_utils.get_temporal_client()

from pydantic import BaseModel
import os
from dotenv import set_key

class SettingsUpdate(BaseModel):
    groq_api_key: str = None
    world_news_api_key: str = None
    youtube_stream_key: str = None

@app.post("/settings")
def update_settings(settings: SettingsUpdate):
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if settings.groq_api_key:
        set_key(env_path, "GROQ_API_KEY", settings.groq_api_key)
    if settings.world_news_api_key:
        set_key(env_path, "WORLD_NEWS_API_KEY", settings.world_news_api_key)
    if settings.youtube_stream_key:
        set_key(env_path, "YOUTUBE_STREAM_KEY", settings.youtube_stream_key)
    return {"status": "success", "message": "API keys updated securely in .env"}

@app.post("/channels", response_model=schemas.ChannelResponse)
async def create_channel(
    channel: schemas.ChannelCreate,
    db: Session = Depends(database.get_db)
):
    try:
        # 1. Create channel in DB
        db_channel = models.Channel(**channel.dict())
        
        # 2. Auto-assign anchor if not provided
        if not db_channel.preferred_anchor_id:
            # Try to assign the first available anchor
            default_anchor = db.query(models.Anchor).filter(models.Anchor.is_active == True).first()
            if default_anchor:
                db_channel.preferred_anchor_id = default_anchor.id
            else:
                # Create a default male anchor if none exist
                default = models.Anchor(name="Default Anchor", gender="male", is_active=True)
                db.add(default)
                db.flush()
                db_channel.preferred_anchor_id = default.id
        
        db.add(db_channel)
        db.commit()
        db.refresh(db_channel)
        return db_channel
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"❌ Error creating channel: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error while creating channel: {error_msg}. Please check if all required columns (owner_id, youtube_stream_key) exist in the 'channels' table."
        )

# --- Anchor Endpoints ---
@app.post("/anchors", response_model=schemas.AnchorResponse)
async def create_anchor(
    anchor: schemas.AnchorCreate,
    db: Session = Depends(database.get_db)
):
    db_anchor = models.Anchor(**anchor.dict())
    db.add(db_anchor)
    db.commit()
    db.refresh(db_anchor)
    return db_anchor

@app.get("/anchors", response_model=list[schemas.AnchorResponse])
async def list_anchors(db: Session = Depends(database.get_db)):
    return db.query(models.Anchor).filter(models.Anchor.is_active == True).all()

@app.put("/channels/{channel_id}/anchor/{anchor_id}")
async def set_channel_anchor(
    channel_id: int,
    anchor_id: int,
    db: Session = Depends(database.get_db)
):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    anchor = db.query(models.Anchor).filter(models.Anchor.id == anchor_id).first()
    if not anchor:
        raise HTTPException(status_code=404, detail="Anchor not found")
    
    channel.preferred_anchor_id = anchor_id
    db.commit()
    return {"status": "success", "message": f"Channel anchor updated to {anchor.name}"}

# --- Advertising Endpoints ---
@app.post("/channels/{channel_id}/ads", response_model=schemas.AdCampaignResponse)
async def create_ad(channel_id: int, ad: schemas.AdCampaignCreate, db: Session = Depends(database.get_db)):
    db_ad = models.AdCampaign(**ad.dict())
    db.add(db_ad)
    db.commit()
    db.refresh(db_ad)
    return db_ad

@app.get("/channels/{channel_id}/ads", response_model=list[schemas.AdCampaignResponse])
async def list_ads(channel_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.AdCampaign).filter(models.AdCampaign.channel_id == channel_id).all()

@app.delete("/ads/{ad_id}")
async def delete_ad(ad_id: int, db: Session = Depends(database.get_db)):
    db_ad = db.query(models.AdCampaign).filter(models.AdCampaign.id == ad_id).first()
    if not db_ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    db.delete(db_ad)
    db.commit()
    return {"status": "deleted"}

import uuid as _uuid

@app.post("/ads/upload-video")
async def upload_ad_video(file: UploadFile = File(...)):
    """Upload an advertisement video file. Returns the server path to use as video_url."""
    allowed_types = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}. Only MP4/MOV/AVI/WebM allowed.")

    ads_dir = "/app/videos/ads"
    os.makedirs(ads_dir, exist_ok=True)

    safe_name = f"{_uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(ads_dir, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    size_mb = len(content) / (1024 * 1024)
    print(f"📼 Ad video uploaded: {safe_name} ({size_mb:.1f} MB)")
    return {"video_url": file_path, "filename": file.filename, "size_mb": round(size_mb, 1)}


@app.post("/channels/{channel_id}/trigger")
async def trigger_news_generation(
    channel_id: int,
    db: Session = Depends(database.get_db),
    temporal_client: Client = Depends(get_temporal_client)
):
    # 1. Verify channel
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # 2. Trigger Temporal Workflow with a stable base workflow ID
    base_workflow_id = f"news-production-{channel_id}"
    workflow_id = base_workflow_id
    
    # Update channel status to "Live"
    channel.is_streaming = True
    db.add(channel)
    db.commit()

    # If an old workflow exists but is not currently RUNNING, start a fresh instance.
    try:
        existing_handle = temporal_client.get_workflow_handle(workflow_id)
        desc = await existing_handle.describe()
        if desc.status.name == "RUNNING":
            return {"status": "already_running", "workflow_id": workflow_id, "message": "News generation is already in progress"}
    except Exception:
        pass
    
    try:
        handle = await temporal_client.start_workflow(
            NewsProductionWorkflow.run,
            {"channel_id": channel_id, "language": channel.language, "stream_key": channel.youtube_stream_key},
            id=workflow_id,
            task_queue="news-task-queue"
        )
        return {"status": "processing", "workflow_id": handle.id}
    except Exception as e:
        error_str = str(e).lower()
        if "already started" in error_str or "workflowalreadystarted" in error_str:
            new_workflow_id = f"{base_workflow_id}-{int(__import__('time').time())}"
            handle = await temporal_client.start_workflow(
                NewsProductionWorkflow.run,
                {"channel_id": channel_id, "language": channel.language, "stream_key": channel.youtube_stream_key},
                id=new_workflow_id,
                task_queue="news-task-queue"
            )
            return {"status": "processing", "workflow_id": handle.id, "message": "Started new workflow instance after stale workflow id"}
        raise

@app.post("/channels/{channel_id}/stop")
async def stop_news_generation(
    channel_id: int,
    db: Session = Depends(database.get_db),
    temporal_client: Client = Depends(get_temporal_client)
):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    import time
    # 1. Update DB 
    channel.is_streaming = False
    db.commit()

    # 2. Kill the stream physical process via worker
    stop_workflow_id = f"stop-channel-{channel_id}-{int(time.time())}"
    await temporal_client.start_workflow(
        StopStreamWorkflow.run,
        channel_id,
        id=stop_workflow_id,
        task_queue="news-task-queue"
    )

    # 3. Soft-fail any pending Temporal generation if needed
    try:
        # We try to terminate the news-gen tracking workflow
        handle = temporal_client.get_workflow_handle(f"news-production-{channel_id}")
        await handle.terminate("User stopped channel from dashboard")
    except Exception:
        pass
        
    return {"status": "stopped", "message": "Channel broadcasting halted."}

@app.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: Session = Depends(database.get_db),
    temporal_client: Client = Depends(get_temporal_client)
):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Stop any broadcast processes immediately
    try:
        await stop_news_generation(channel_id, db, temporal_client)
    except Exception:
        pass
        
    db.delete(channel)
    db.commit()
    
    return {"status": "deleted", "message": "Channel permanently removed."}

@app.get("/channels", response_model=list[schemas.ChannelResponse])
def list_channels(db: Session = Depends(database.get_db)):
    return db.query(models.Channel).all()


