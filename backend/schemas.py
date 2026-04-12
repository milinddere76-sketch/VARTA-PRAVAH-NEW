from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class AnchorBase(BaseModel):
    name: str
    gender: str
    description: Optional[str] = None
    is_active: Optional[bool] = True

class AnchorResponse(AnchorBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ChannelBase(BaseModel):
    name: str
    language: Optional[str] = "Marathi"
    youtube_stream_key: Optional[str] = None
    owner_id: int
    preferred_anchor_id: Optional[int] = None

class ChannelCreate(ChannelBase):
    pass

class ChannelResponse(ChannelBase):
    id: int
    is_streaming: bool
    model_config = ConfigDict(from_attributes=True)

class AdCampaignBase(BaseModel):
    name: str
    video_url: str
    scheduled_hours: str
    is_active: Optional[bool] = True
    channel_id: int
    preferred_anchor_id: Optional[int] = None

class AdCampaignCreate(AdCampaignBase):
    pass

class AdCampaignResponse(AdCampaignBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class StreamKeyUpdate(BaseModel):
    youtube_stream_key: str
