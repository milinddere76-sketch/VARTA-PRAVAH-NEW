from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
import os
import subprocess
import socket
import time
import uuid as _uuid
from sqlalchemy.orm import Session
from temporalio.client import Client
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from dotenv import set_key

import database, models, schemas, temporal_utils
from streaming_engine.workflows import NewsProductionWorkflow, StopStreamWorkflow
from streamer import Streamer

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

app = FastAPI(title="VartaPravah API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SettingsUpdate(BaseModel):
    groq_api_key: str = None
    world_news_api_key: str = None
    youtube_stream_key: str = None

#  Metadata 
@app.get("/")
def read_root():
    return {"status": "VartaPravah API Engine Online - Pillow-Overlay", "version": "1.2.1"}

#  Diagnostics 
@app.get("/debug/health")
async def server_health_check(db: Session = Depends(database.get_db)):
    """Diagnostic endpoint to check streamer environment."""
    checks = {}
    
    # 1. Connection check
    try:
        with socket.create_connection(("a.rtmp.youtube.com", 1935), timeout=5):
            checks["youtube_rtmp_1935"] = "REACHABLE"
    except Exception as e:
        checks["youtube_rtmp_1935"] = f"BLOCKED: {str(e)}"
    
    # 2. Filesystem check
    promo_path = "/app/videos/promo.mp4"
    checks["promo_exists"] = os.path.exists(promo_path)
    if checks["promo_exists"]:
        checks["promo_size_mb"] = os.path.getsize(promo_path) / (1024*1024)
        
    # 3. Stream Attempt
    channel = db.query(models.Channel).filter(models.Channel.id == 1).first()
    if channel and checks["promo_exists"]:
        try:
            s = Streamer(channel.youtube_stream_key, 1)
            s.current_video = promo_path
            s.start_stream()
            time.sleep(3)
            is_alive = s.process.poll() is None
            checks["attempt_stream_alive"] = is_alive
            s.stop_stream()
        except Exception as e:
            checks["attempt_stream_error"] = str(e)
            
    return checks

@app.get("/debug/logs/worker")
async def get_worker_status():
    status_file = "/app/videos/worker_status.txt"
    if not os.path.exists(status_file):
        return {"status": "Worker not yet started or heartbeat file missing."}
    try:
        with open(status_file, "r") as f:
            content = f.read()
        return {"heartbeat": content}
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/files")
async def list_videos():
    try:
        video_dir = "/app/videos"
        if not os.path.exists(video_dir): return {"files": []}
        files = os.listdir(video_dir)
        return {"files": [f"{f} ({os.path.getsize(os.path.join(video_dir, f))/1024:.1f} KB)" for f in files]}
    except:
        return {"error": "videos dir not found"}

#  System Control 
@app.post("/system/reset")
async def system_nuclear_reset(db: Session = Depends(database.get_db)):
    """Wipes all generated content and kills all stream processes."""
    results = {}
    try:
        subprocess.run(["pkill", "-9", "-f", "ffmpeg"], capture_output=True)
        results["ffmpeg_killed"] = True
    except:
        results["ffmpeg_killed"] = False

    try:
        db.query(models.Channel).update({models.Channel.is_streaming: False})
        db.commit()
        results["db_reset"] = True
    except:
        results["db_reset"] = False

    video_dir = "/app/videos"
    try:
        if os.path.exists(video_dir):
            for filename in os.listdir(video_dir):
                file_path = os.path.join(video_dir, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
        results["videos_wiped"] = True
    except Exception as e:
        results["videos_wiped"] = f"Partial: {str(e)}"

    return {"status": "success", "summary": results}

#  Settings 
@app.post("/settings")
def update_settings(data: dict):
    """Update API keys live."""
    try:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        # Direct set using set_key for reliability
        if data.get("groq_api_key"):
            set_key(env_path, "GROQ_API_KEY", data["groq_api_key"])
            os.environ["GROQ_API_KEY"] = data["groq_api_key"]
        if data.get("world_news_api_key"):
            set_key(env_path, "WORLD_NEWS_API_KEY", data["world_news_api_key"])
            os.environ["WORLD_NEWS_API_KEY"] = data["world_news_api_key"]
        return {"status": "success", "message": "API keys updated and saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#  Channel Management 
@app.get("/channels", response_model=list[schemas.ChannelResponse])
def list_channels(db: Session = Depends(database.get_db)):
    return db.query(models.Channel).all()

@app.post("/channels", response_model=schemas.ChannelResponse)
async def create_channel(channel: schemas.ChannelCreate, db: Session = Depends(database.get_db)):
    db_channel = models.Channel(**channel.dict())
    if not db_channel.preferred_anchor_id:
        default_anchor = db.query(models.Anchor).filter(models.Anchor.is_active == True).first()
        if not default_anchor:
            default_anchor = models.Anchor(name="Priya Desai", gender="female", is_active=True)
            db.add(default_anchor)
            db.flush()
        db_channel.preferred_anchor_id = default_anchor.id
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel

@app.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, db: Session = Depends(database.get_db)):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel: raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(channel)
    db.commit()
    return {"status": "deleted"}

@app.put("/channels/{channel_id}/stream-key")
async def set_channel_stream_key(channel_id: int, stream_key: str, db: Session = Depends(database.get_db)):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel: raise HTTPException(status_code=404, detail="Channel not found")
    channel.youtube_stream_key = stream_key
    db.commit()
    return {"status": "success", "message": "Stream key updated."}

@app.put("/channels/{channel_id}/anchor/{anchor_id}")
async def set_channel_anchor(channel_id: int, anchor_id: int, db: Session = Depends(database.get_db)):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    anchor = db.query(models.Anchor).filter(models.Anchor.id == anchor_id).first()
    if not channel or not anchor: raise HTTPException(status_code=404, detail="Not found")
    channel.preferred_anchor_id = anchor_id
    db.commit()
    return {"status": "success", "message": f"Anchor set to {anchor.name}"}

#  Broadcast Control 
async def get_temporal_client():
    return await temporal_utils.get_temporal_client()

@app.post("/channels/{channel_id}/trigger")
async def trigger_news_generation(
    channel_id: int,
    db: Session = Depends(database.get_db),
    temporal_client: Client = Depends(get_temporal_client)
):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel: raise HTTPException(status_code=404, detail="Channel not found")
    
    workflow_id = f"news-production-{channel_id}"
    channel.is_streaming = True
    db.commit()

    try:
        handle = await temporal_client.start_workflow(
            NewsProductionWorkflow.run,
            {"channel_id": channel_id, "language": channel.language, "stream_key": channel.youtube_stream_key},
            id=workflow_id,
            task_queue="news-task-queue"
        )
        return {"status": "processing", "workflow_id": handle.id}
    except Exception as e:
        if "already started" in str(e).lower():
            return {"status": "already_running", "workflow_id": workflow_id}
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/channels/{channel_id}/stop")
async def stop_news_generation(
    channel_id: int,
    db: Session = Depends(database.get_db),
    temporal_client: Client = Depends(get_temporal_client)
):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel: raise HTTPException(status_code=404, detail="Channel not found")
    
    channel.is_streaming = False
    db.commit()

    # Kill processes via worker
    await temporal_client.start_workflow(
        StopStreamWorkflow.run,
        channel_id,
        id=f"stop-channel-{channel_id}-{int(time.time())}",
        task_queue="news-task-queue"
    )
    
    try:
        handle = temporal_client.get_workflow_handle(f"news-production-{channel_id}")
        await handle.terminate("User stopped channel")
    except: pass
        
    return {"status": "stopped"}

#  Ads 
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
    if not db_ad: raise HTTPException(status_code=404, detail="Ad not found")
    db.delete(db_ad)
    db.commit()
    return {"status": "deleted"}

@app.post("/ads/upload-video")
async def upload_ad_video(file: UploadFile = File(...)):
    ads_dir = "/app/videos/ads"
    os.makedirs(ads_dir, exist_ok=True)
    safe_name = f"{_uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(ads_dir, safe_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return {"video_url": file_path, "filename": file.filename, "size_mb": round(len(content)/(1024*1024), 1)}
