from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    language = Column(String)
    youtube_stream_key = Column(String)
    is_streaming = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))
    preferred_anchor_id = Column(Integer, ForeignKey("anchors.id"), nullable=True)

    owner = relationship("User")
    preferred_anchor = relationship("Anchor")

class Anchor(Base):
    __tablename__ = "anchors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    gender = Column(String)  # "male" or "female"
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    video_url = Column(String)
    scheduled_hours = Column(String)  # e.g., "08,12,18,21"
    is_active = Column(Boolean, default=True)
    channel_id = Column(Integer, ForeignKey("channels.id"))
    preferred_anchor_id = Column(Integer, ForeignKey("anchors.id"), nullable=True)

    channel = relationship("Channel")
    preferred_anchor = relationship("Anchor")