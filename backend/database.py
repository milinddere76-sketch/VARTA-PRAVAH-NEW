import os
import time
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from models import Base
from dotenv import load_dotenv

load_dotenv()

engine = None
SessionLocal = None

def is_db_open(url, timeout=0.5):
    """Quick socket probe for Postgres."""
    try:
        # Extract host and port from postgresql://root:password@host:port/dbname
        host_port = url.split('@')[-1].split('/')[0]
        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host, port = host_port, 5432
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except:
        return False

def get_engine():
    """
    🏗️ Steel-Hardened Database Prober
    Finds the correct Postgres connection in any environment (Coolify, Local, or Docker).
    """
    possible_urls = [
        os.getenv("DATABASE_URL"),
        os.getenv("SQLITE_URL"),
        "postgresql://root:password@postgres:5432/temporal",
        "postgresql://root:password@localhost:5432/temporal",
        "postgresql://root:password@postgres-t892o397h64afn1mgn4lndi3-234723873492:5432/temporal"
    ]
    
    for url in [u for u in possible_urls if u]:
        if url.startswith("sqlite"):
            print(f"📦 Using local SQLite database at {url}")
            return create_engine(url, connect_args={"check_same_thread": False}, pool_pre_ping=True)

        print(f"📡 Speed Probing Database at {url.split('@')[-1]}...")
        if not is_db_open(url):
            print(f"⏩ Skipping {url.split('@')[-1]} (Port closed/Unreachable)")
            continue

        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                print(f"✅ Database Connected Successfully at {url.split('@')[-1]}!")
                return engine
        except (OperationalError, Exception) as e:
            print(f"❌ Connection failed for {url.split('@')[-1]}: {str(e)[:50]}...")
            continue

    sqlite_path = os.getenv("SQLITE_URL") or f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dev.db')}"
    print(f"📦 No PostgreSQL host reachable; falling back to local SQLite at {sqlite_path}")
    return create_engine(sqlite_path, connect_args={"check_same_thread": False}, pool_pre_ping=True)


def get_session_local():
    global engine, SessionLocal
    if engine is None:
        engine = get_engine()
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables with safety checks."""
    get_session_local()
    Base.metadata.create_all(bind=engine)
