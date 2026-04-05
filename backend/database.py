import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base
from dotenv import load_dotenv

load_dotenv()

# PRODUCTION: Point to 'postgres' host for internal Docker networking
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://root:password@postgres:5432/temporal"

def get_engine_with_retry(url, max_retries=30, delay=1):
    """Wait-for-Database Shield: Attempt to connect to Postgres with a retry loop."""
    last_error = None
    for i in range(max_retries):
        try:
            temp_engine = create_engine(url, pool_pre_ping=True)
            # Test the connection immediately
            with temp_engine.connect() as conn:
                print(f"Database is ready (Attempt {i+1})! Proceeding to newsroom initialization...")
                return temp_engine
        except Exception as e:
            last_error = e
            if i % 5 == 0:
                print(f"Waiting for database to wake up... (Attempt {i+1}/{max_retries})")
            time.sleep(delay)
    
    print(f"FATAL: Database failed to stabilize after {max_retries} seconds.")
    raise last_error

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
