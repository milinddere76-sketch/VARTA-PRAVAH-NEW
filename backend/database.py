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

# ================= ENGINE BUILDER ================= #

_CACHED_ENGINE_URL = None

def get_engine():
    global engine, _CACHED_ENGINE_URL
    
    if engine is not None:
        return engine

    # 1. PRIORITY: Use cached URL if we already found one that works
    if _CACHED_ENGINE_URL:
        engine = create_engine(_CACHED_ENGINE_URL, pool_pre_ping=True)
        return engine

    possible_urls = [
        os.getenv("DATABASE_URL"),
        os.getenv("SQLITE_URL"),
        "postgresql://root:password@postgres:5432/temporal",
        "postgresql://root:password@localhost:5432/temporal",
    ]

    for url in filter(None, possible_urls):
        # Socket check with very fast timeout (200ms) to avoid hanging
        if url.startswith("postgresql"):
            host_info = url.split('@')[-1].split('/')[0]
            if not is_db_open(url, timeout=0.2):
                continue
        
        try:
            if url.startswith("sqlite"):
                new_engine = create_engine(url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
            else:
                new_engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
            
            with new_engine.connect() as conn:
                print(f"✅ Connected to {url.split('@')[-1] if '@' in url else url}")
                engine = new_engine
                _CACHED_ENGINE_URL = url # Cache for next time
                return engine
        except Exception:
            continue

    # ================= FALLBACK ================= #
    sqlite_path = "sqlite:///./dev.db"
    print(f"⚠️ Falling back to SQLite: {sqlite_path}")
    engine = create_engine(sqlite_path, connect_args={"check_same_thread": False}, pool_pre_ping=True)
    return engine


# ================= SESSION ================= #

def get_session_local():
    global SessionLocal
    if engine is None:
        get_engine()
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


# ================= DEPENDENCY ================= #

def get_db():
    try:
        db = get_session_local()()
        yield db
    except Exception as e:
        print(f"❌ DB Session Error: {e}")
        raise
    finally:
        db.close()


# ================= INIT ================= #

def col_exists(conn, table_name, column_name):
    """Check if a column exists in a table (SQLAlchemy 2.0 compatible)"""
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns

def init_db():
    from sqlalchemy import text, inspect
    try:
        engine = get_engine()
        print("📦 Initializing database tables...")

        # 1. Create tables in explicit dependency order to avoid FK issues.
        #    We import models here to ensure all are registered on Base.metadata.
        import models  # noqa: F401 - registers all ORM classes

        # Create independent tables first, then dependent ones
        tables_in_order = [
            "users",
            "anchors",
            "channels",
            "ad_campaigns",
        ]
        insp = inspect(engine)
        existing = insp.get_table_names()
        for tname in tables_in_order:
            if tname not in existing:
                # Create only this specific table
                if tname in Base.metadata.tables:
                    Base.metadata.tables[tname].create(bind=engine)
                    print(f"✅ Created table '{tname}'")

        # Also catch any remaining tables (e.g. future additions)
        Base.metadata.create_all(bind=engine)

        # 2. Add missing columns without FK constraints in ALTER TABLE.
        #    SQLAlchemy enforces FK relationships at the ORM level, so the
        #    bare INTEGER column is functionally identical and avoids errors
        #    when the referenced table might not exist yet in legacy DBs.
        with engine.connect() as conn:
            # --- CHANNELS TABLE ---
            channels_cols = [
                ("owner_id",            "INTEGER"),
                ("preferred_anchor_id", "INTEGER"),
                ("youtube_stream_key",  "VARCHAR"),
            ]
            for col_name, col_type in channels_cols:
                if not col_exists(conn, "channels", col_name):
                    try:
                        print(f"📝 Adding missing column 'channels.{col_name}'...")
                        conn.execute(text(f"ALTER TABLE channels ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f"✅ Added 'channels.{col_name}'")
                    except Exception as e:
                        print(f"⚠️ Could not add 'channels.{col_name}': {e}")
                else:
                    print(f"✅ Column 'channels.{col_name}' already exists.")

            # --- AD_CAMPAIGNS TABLE ---
            if not col_exists(conn, "ad_campaigns", "preferred_anchor_id"):
                try:
                    print("📝 Adding 'ad_campaigns.preferred_anchor_id'...")
                    conn.execute(text("ALTER TABLE ad_campaigns ADD COLUMN preferred_anchor_id INTEGER"))
                    conn.commit()
                    print("✅ Added 'ad_campaigns.preferred_anchor_id'")
                except Exception as e:
                    print(f"⚠️ Could not add ad_campaigns column: {e}")
            else:
                print("✅ Column 'ad_campaigns.preferred_anchor_id' already exists.")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise  # Re-raise so startup fails loudly rather than silently