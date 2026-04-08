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

import socket

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
        "postgresql://root:password@postgres:5432/temporal",
        "postgresql://root:password@localhost:5432/temporal",
        "postgresql://root:password@postgres-t892o397h64afn1mgn4lndi3-234723873492:5432/temporal"
    ]
    
    for url in [u for u in possible_urls if u]:
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
