#!/usr/bin/env python3
import os
import sys

sys.path.append('.')

# ---------------------------
# ENV SETUP (SAFE)
# ---------------------------
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:password@localhost:5432/temporal"

if not os.getenv("SQLITE_URL"):
    os.environ["SQLITE_URL"] = "sqlite:///dev.db"

# ---------------------------
# IMPORTS
# ---------------------------
from database import get_engine, get_session_local
from models import Channel, User, Base

# ---------------------------
# INIT DB
# ---------------------------
print("🔧 Initializing database...")
engine = get_engine()
Base.metadata.create_all(bind=engine)

SessionLocal = get_session_local()
db = SessionLocal()

try:
    # -----------------------
    # CHECK USERS
    # -----------------------
    users = db.query(User).all()

    if not users:
        print("⚠️ No users found. Creating default user...")

        default_user = User(
            id=1,
            email="admin@vartapravah.com",
            hashed_password="admin123",
            full_name="Admin",
            is_active=True
        )

        db.add(default_user)
        db.commit()
        db.refresh(default_user)

        users = [default_user]

    # -----------------------
    # CHECK CHANNELS
    # -----------------------
    channels = db.query(Channel).all()

    print("\n📊 Database Status:")
    print(f"Users: {len(users)}")
    for user in users:
        print(f"  - {user.email} (ID: {user.id})")

    print(f"Channels: {len(channels)}")
    for channel in channels:
        print(f"  - {channel.name} (ID: {channel.id}, streaming: {channel.is_streaming})")

    # -----------------------
    # CREATE CHANNEL IF NONE
    # -----------------------
    if not channels:
        print("\n⚠️ No channels found. Creating default channel...")

        channel = Channel(
            name="Varta Pravah Live",
            language="Marathi",
            youtube_stream_key="your-stream-key-here",
            is_streaming=False,
            owner_id=users[0].id
        )

        db.add(channel)
        db.commit()
        db.refresh(channel)

        print(f"✅ Created channel: {channel.name} (ID: {channel.id})")

    else:
        print("\n✅ Channels already exist.")

except Exception as e:
    print(f"❌ Error: {e}")

finally:
    db.close()
    print("\n🔒 Database session closed.")