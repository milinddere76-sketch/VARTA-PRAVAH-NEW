from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AnchorBase(BaseModel):
    name: str
    gender: str
    description: Optional[str] = None

class AnchorCreate(AnchorBase):
    pass

class AnchorResponse(AnchorBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class ChannelBase(BaseModel):
    name: str
    language: str
    youtube_stream_key: str
    preferred_anchor_id: Optional[int] = None

class ChannelCreate(ChannelBase):
    owner_id: int

class ChannelResponse(ChannelBase):
    id: int
    is_streaming: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AdCampaignBase(BaseModel):
    name: str
    video_url: str
    scheduled_hours: str

class AdCampaignCreate(AdCampaignBase):
    channel_id: int

class AdCampaignResponse(AdCampaignBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True