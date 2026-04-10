import os
import time
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

engine = None
SessionLocal = None


# ================= SOCKET CHECK ================= #

def is_db_open(url, timeout=0.5):
    try:
        host_info = url.split('@')[-1].split('/')[0]

        if ':' in host_info:
            host, port = host_info.split(':')
        else:
            host, port = host_info, 5432

        with socket.create_connection((host, int(port)), timeout=timeout):
            return True

    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


# ================= ENGINE BUILDER ================= #

def get_engine():
    global engine

    possible_urls = [
        os.getenv("DATABASE_URL"),
        os.getenv("SQLITE_URL"),
        "postgresql://root:password@postgres:5432/temporal",
        "postgresql://root:password@localhost:5432/temporal",
    ]

    for url in filter(None, possible_urls):

        if url.startswith("sqlite"):
            print(f"📦 Using SQLite: {url}")
            engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True
            )
            return engine

        host_info = url.split('@')[-1]
        print(f"📡 Checking DB: {host_info}")

        if not is_db_open(url):
            print(f"⏩ Skipping {host_info} (unreachable)")
            continue

        try:
            engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )

            with engine.connect():
                print(f"✅ Connected to {host_info}")
                return engine

        except OperationalError as e:
            print(f"❌ DB error {host_info}: {str(e)[:60]}")
            continue

    # ================= FALLBACK ================= #

    sqlite_path = os.getenv("SQLITE_URL")

    if not sqlite_path:
        sqlite_path = "sqlite:///./dev.db"  # safer for Docker

    print(f"⚠️ Falling back to SQLite: {sqlite_path}")

    engine = create_engine(
        sqlite_path,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )

    return engine


# ================= SESSION ================= #

def get_session_local():
    global SessionLocal

    if engine is None:
        get_engine()

    if SessionLocal is None:
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )

    return SessionLocal


# ================= DEPENDENCY ================= #

def get_db():
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


# ================= INIT ================= #

def init_db():
    from sqlalchemy import text
    engine = get_engine()
    
    # 1. Create missing tables (e.g., 'anchors')
    print("📦 Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Add missing columns (Self-Healing Migration)
    with engine.connect() as conn:
        # --- CHANNELS TABLE ---
        columns_to_add = [
            ("owner_id", "INTEGER REFERENCES users(id)"),
            ("preferred_anchor_id", "INTEGER REFERENCES anchors(id)"),
            ("youtube_stream_key", "VARCHAR")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                print(f"📝 Syncing 'channels.{col_name}' schema...")
                conn.execute(text(f"ALTER TABLE channels ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"✅ Added '{col_name}' to 'channels'")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"✅ 'channels.{col_name}' schema is up to date.")
                else:
                    print(f"⚠️ Warning updating 'channels.{col_name}': {e}")

        # --- AD_CAMPAIGNS TABLE ---
        try:
            print("📝 Syncing 'ad_campaigns' schema...")
            conn.execute(text("ALTER TABLE ad_campaigns ADD COLUMN preferred_anchor_id INTEGER REFERENCES anchors(id)"))
            conn.commit()
            print("✅ Added 'preferred_anchor_id' to 'ad_campaigns'")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("✅ 'ad_campaigns' schema is up to date.")
            else:
                print(f"⚠️ Warning updating 'ad_campaigns': {e}")