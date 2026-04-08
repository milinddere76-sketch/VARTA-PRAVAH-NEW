#!/usr/bin/env python3
import os
import sys
sys.path.append('.')

# Set environment variables for local testing
os.environ['DATABASE_URL'] = 'postgresql://root:password@localhost:5432/temporal'
os.environ['SQLITE_URL'] = 'sqlite:///dev.db'

from database import get_engine
from models import Channel, User, Base

# Create tables
engine = get_engine()
Base.metadata.create_all(bind=engine)

# Seed database
from database import get_session_local
SessionLocal = get_session_local()
db = SessionLocal()

# Check existing data
users = db.query(User).all()
channels = db.query(Channel).all()

print("Database status:")
print(f"Users: {len(users)}")
for user in users:
    print(f"  - {user.email} (ID: {user.id})")

print(f"Channels: {len(channels)}")
for channel in channels:
    print(f"  - {channel.name} (ID: {channel.id}, streaming: {channel.is_streaming})")

if not channels:
    print("No channels found, creating one...")
    # Create a test channel
    channel = Channel(
        name="Test Channel",
        youtube_stream_key="test-key",
        is_streaming=False,
        owner_id=users[0].id if users else 1
    )
    db.add(channel)
    db.commit()
    print(f"Created channel: {channel.name} (ID: {channel.id})")
else:
    print("Channels already exist.")

db.close()