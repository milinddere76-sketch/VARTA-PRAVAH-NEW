from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

# -------------------- USER MODEL --------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)

    # Relationship (One User → Many Channels)
    channels = relationship("Channel", back_populates="owner", cascade="all, delete")


# -------------------- CHANNEL MODEL --------------------
class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    language = Column(String(50), nullable=False)
    youtube_stream_key = Column(String(255), nullable=False)
    is_streaming = Column(Boolean, default=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    # Relationships
    owner = relationship("User", back_populates="channels")
    ads = relationship("AdCampaign", back_populates="channel", cascade="all, delete")


# -------------------- AD CAMPAIGN MODEL --------------------
class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    video_url = Column(String(500), nullable=False)

    # Store as comma-separated hours like: "08,12,18"
    scheduled_hours = Column(String(100), nullable=False)

    is_active = Column(Boolean, default=True)

    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"))

    # Relationship
    channel = relationship("Channel", back_populates="ads")