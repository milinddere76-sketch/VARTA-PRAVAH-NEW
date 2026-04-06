from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    tier = Column(String, default="free")  # free, pro, business
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    channels = relationship("Channel", back_populates="owner")

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    language = Column(String, default="Marathi")
    youtube_stream_key = Column(String, nullable=True)
    is_streaming = Column(Boolean, default=False)
    
    # S3 URL for the base anchor video used for this channel
    base_anchor_url = Column(String, nullable=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="channels")
    
    segments = relationship("Segment", back_populates="channel")
    ad_campaigns = relationship("AdCampaign", back_populates="channel")
    created_at = Column(DateTime, default=datetime.utcnow)

class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"))
    channel = relationship("Channel", back_populates="ad_campaigns")

    name = Column(String, nullable=False)
    video_url = Column(String, nullable=False) # S3 or Local URL
    
    # Schedule logic: Simple hour-based triggers (e.g., "08:00,12:00,20:00")
    scheduled_hours = Column(String, nullable=False) 
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Segment(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"))
    channel = relationship("Channel", back_populates="segments")
    
    headline = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    video_url = Column(String, nullable=True)  # S3 URL to finished segment
    
    status = Column(String, default="pending")  # pending, generating, ready, streaming, expired
    created_at = Column(DateTime, default=datetime.utcnow)
