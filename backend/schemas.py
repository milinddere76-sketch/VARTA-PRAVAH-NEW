from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ================= CHANNEL ================= #

class ChannelBase(BaseModel):
    name: str
    language: str
    youtube_stream_key: str


class ChannelCreate(ChannelBase):
    owner_id: int


class ChannelResponse(ChannelBase):
    id: int
    is_streaming: bool = False
    created_at: datetime

    class Config:
        # ✅ Works for BOTH Pydantic v1 & v2
        orm_mode = True
        from_attributes = True


# ================= ADS ================= #

class AdCampaignBase(BaseModel):
    name: str
    video_url: str

    # ✅ FIX: safer than string
    scheduled_hours: List[int]


class AdCampaignCreate(AdCampaignBase):
    channel_id: int


class AdCampaignResponse(AdCampaignBase):
    id: int
    is_active: bool = True

    class Config:
        orm_mode = True
        from_attributes = True