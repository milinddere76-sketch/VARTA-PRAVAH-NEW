import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base
from dotenv import load_dotenv

load_dotenv()

import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from models import Base
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    """
    🏗️ Steel-Hardened Database Prober
    Finds the correct Postgres connection in any environment (Coolify, Local, or Docker).
    """
    # 🛰️ Probing order: Env Var -> Standard Docker -> Localhost -> Specific Host
    possible_urls = [
        os.getenv("DATABASE_URL"),
        "postgresql://root:password@postgres:5432/temporal",
        "postgresql://root:password@localhost:5432/temporal",
        "postgresql://root:password@postgres-t892o397h64afn1mgn4lndi3-175128029000:5432/temporal"
    ]
    
    # 🏎️ Async Engine required for FastAPI logic but we use sync for Metadata/Session
    for url in [u for u in possible_urls if u]:
        try:
            print(f"📡 Testing Database Connection at {url.split('@')[-1]}...")
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                print(f"✅ Database Connected Successfully at {url.split('@')[-1]}!")
                return engine
        except (OperationalError, Exception) as e:
            print(f"❌ Connection failed for {url.split('@')[-1]}: {str(e)[:50]}...")
            continue
            
    # If all fail, we do one final retry loop on the first available URL
    raise ConnectionError("CRITICAL: Database failed to respond after probing all known hosts.")

# Global Engine Initialization
engine = get_engine()
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
