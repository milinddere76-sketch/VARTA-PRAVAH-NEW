from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)

class Anchor(Base):
    __tablename__ = "anchors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    gender = Column(String) # male / female
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    language = Column(String, default="Marathi")
    youtube_stream_key = Column(String, nullable=True)
    is_streaming = Column(Boolean, default=False)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    preferred_anchor_id = Column(Integer, ForeignKey("anchors.id"), nullable=True)

class AdCampaign(Base):
    __tablename__ = "ad_campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    video_url = Column(String)
    start_hour = Column(Integer) # 0-23
    end_hour = Column(Integer)   # 0-23
    is_active = Column(Boolean, default=True)
    
    channel_id = Column(Integer, ForeignKey("channels.id"))
    preferred_anchor_id = Column(Integer, ForeignKey("anchors.id"), nullable=True)
