import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base
from dotenv import load_dotenv

load_dotenv()

# PRODUCTION: Point to 'postgres' host for internal Docker networking
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://root:password@postgres:5432/temporal"

def get_engine_with_retry(url, max_retries=15, delay=2):
    """Wait-for-Database Shield: Attempt to connect silently with a retry loop."""
    for i in range(max_retries):
        try:
            # We use a temporary engine to check connectivity without leaking failures
            temp_engine = create_engine(url, pool_pre_ping=True)
            with temp_engine.connect():
                return temp_engine
        except Exception:
            # No print here to keep the logs clean and 'Green'
            time.sleep(delay)
    
    # Only raise if truly stalled after 30 seconds
    raise ConnectionError("Database failed to respond in time.")

# Global Engine Initialization (Steel Hardened)
engine = get_engine_with_retry(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables with safety checks."""
    Base.metadata.create_all(bind=engine)
