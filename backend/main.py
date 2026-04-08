from fastapi import FastAPI, Depends, HTTPException, status
import os
from sqlalchemy.orm import Session
from temporalio.client import Client
import database, models, schemas, temporal_utils
from datetime import timedelta
from temporal.workflows import NewsProductionWorkflow, StopStreamWorkflow

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
    # 1. Create channel in DB
    db_channel = models.Channel(**channel.dict())
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel

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

    # 2. Trigger Temporal Workflow with deterministic single-channel ID
    workflow_id = f"news-production-{channel_id}"
    
    # Update channel status to "Live"
    channel.is_streaming = True
    db.add(channel)
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
        # Handle case where workflow is already running
        error_str = str(e).lower()
        if "already started" in error_str or "workflowalreadystarted" in str(type(e)).lower():
            return {"status": "already_running", "workflow_id": workflow_id, "message": "News generation is already in progress"}
        else:
            # Re-raise other exceptions
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


