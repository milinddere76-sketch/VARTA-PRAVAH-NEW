from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    tier: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChannelCreate(BaseModel):
    name: str
    language: str = "Marathi"
    youtube_stream_key: Optional[str] = None
    owner_id: int

class ChannelResponse(BaseModel):
    id: int
    name: str
    language: str
    youtube_stream_key: Optional[str]
    is_streaming: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SegmentResponse(BaseModel):
    id: int
    headline: str
    video_url: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class AdCampaignCreate(BaseModel):
    name: str
    video_url: str
    scheduled_hours: str # "08:00,12:00,20:00"
    channel_id: int

class AdCampaignResponse(BaseModel):
    id: int
    name: str
    video_url: str
    scheduled_hours: str
    is_active: bool
    channel_id: int

    class Config:
        from_attributes = True
