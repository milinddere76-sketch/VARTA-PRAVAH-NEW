from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from temporalio.client import Client
import database, models, schemas
from datetime import timedelta
from temporal.workflows import NewsProductionWorkflow

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
    # Use a shared client for efficiency
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    return await Client.connect(temporal_host)

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

    # 2. Trigger Temporal Workflow with unique ID
    import time
    workflow_id = f"news-gen-{channel_id}-{int(time.time())}"
    
    # Update channel status to "Live"
    channel.is_streaming = True
    db.add(channel)
    db.commit()
    
    handle = await temporal_client.start_workflow(
        NewsProductionWorkflow.run,
        {"channel_id": channel_id, "language": channel.language, "stream_key": channel.youtube_stream_key},
        id=workflow_id,
        task_queue="news-task-queue"
    )
    
    return {"status": "processing", "workflow_id": handle.id}

@app.get("/channels", response_model=list[schemas.ChannelResponse])
def list_channels(db: Session = Depends(database.get_db)):
    return db.query(models.Channel).all()
