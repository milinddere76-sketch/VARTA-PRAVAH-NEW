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
        "postgresql+psycopg://postgres:varta_pravah_secure_99@postgres:5432/temporal", # Priority 1: Orchestrated network
        os.getenv("DATABASE_URL"),                                     # Priority 2: Env override
        "postgresql+psycopg://postgres:varta_pravah_secure_99@localhost:5432/temporal",# Priority 3: Local dev
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
                print(f" Connected to {url.split('@')[-1] if '@' in url else url}")
                engine = new_engine
                _CACHED_ENGINE_URL = url # Cache for next time
                return engine
        except Exception:
            continue

    # ================= FALLBACK ================= #
    sqlite_path = "sqlite:///./dev.db"
    print(f" Falling back to SQLite: {sqlite_path}")
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
        print(f" DB Session Error: {e}")
        raise
    finally:
        db.close()


# ================= INIT ================= #

def col_exists(eng, table_name, column_name):
    """
    Check if a column exists in a table.
    IMPORTANT: In SQLAlchemy 2.0, inspect() must receive the ENGINE, not a Connection.
    """
    from sqlalchemy import inspect as sa_inspect
    try:
        inspector = sa_inspect(eng)
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        # Table doesn't exist or other error  treat as "column doesn't exist"
        return False

def _safe_add_column(engine, conn, table: str, col_name: str, col_type: str):
    """Add a column to a table if it doesn't already exist. Never raises."""
    from sqlalchemy import text
    try:
        if not col_exists(engine, table, col_name):
            print(f" Adding missing column '{table}.{col_name}'...")
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
            conn.commit()
            print(f" Added '{table}.{col_name}'")
        else:
            print(f" Column '{table}.{col_name}' already exists.")
    except Exception as e:
        print(f" Could not add '{table}.{col_name}': {e}")

def init_db():
    from sqlalchemy import inspect as sa_inspect
    max_retries = 10
    retry_interval = 3
    
    eng = None
    for i in range(max_retries):
        try:
            eng = get_engine()
            # Test connection
            with eng.connect() as conn:
                break
        except Exception as e:
            if i == max_retries - 1:
                print(f" Database connection failed after {max_retries} attempts: {e}")
                raise
            print(f" Database not ready (Attempt {i+1}/{max_retries}). Retrying in {retry_interval}s...")
            time.sleep(retry_interval)

    try:
        print(" Initializing database tables...")

        # 1. Import all models so they register on Base.metadata
        import models  # noqa: F401

        # 2. Create tables in dependency order (avoids FK resolution issues)
        tables_in_order = ["users", "anchors", "channels", "ad_campaigns"]
        insp = sa_inspect(eng)
        existing = insp.get_table_names()
        for tname in tables_in_order:
            if tname not in existing:
                if tname in Base.metadata.tables:
                    Base.metadata.tables[tname].create(bind=eng)
                    print(f" Created table '{tname}'")

        # Catch any remaining tables not in the ordered list
        Base.metadata.create_all(bind=eng)

        # 3. Add any missing columns (no FK in ALTER TABLE  SQLAlchemy ORM handles FKs)
        with eng.connect() as conn:
            # --- USERS ---
            _safe_add_column(eng, conn, "users", "full_name",        "VARCHAR")
            _safe_add_column(eng, conn, "users", "is_active",        "BOOLEAN DEFAULT TRUE")

            # --- ANCHORS ---
            _safe_add_column(eng, conn, "anchors", "portrait_url",   "VARCHAR")
            _safe_add_column(eng, conn, "anchors", "description",    "VARCHAR")
            _safe_add_column(eng, conn, "anchors", "is_active",      "BOOLEAN DEFAULT TRUE")
            _safe_add_column(eng, conn, "anchors", "created_at",     "TIMESTAMP DEFAULT NOW()")

            # --- CHANNELS ---
            _safe_add_column(eng, conn, "channels", "owner_id",           "INTEGER")
            _safe_add_column(eng, conn, "channels", "preferred_anchor_id","INTEGER")
            _safe_add_column(eng, conn, "channels", "youtube_stream_key", "VARCHAR")

            # --- AD_CAMPAIGNS ---
            _safe_add_column(eng, conn, "ad_campaigns", "scheduled_hours",        "VARCHAR")
            _safe_add_column(eng, conn, "ad_campaigns", "preferred_anchor_id",    "INTEGER")

        print(" Database initialization complete.")

    except Exception as e:
        # Log but NEVER raise  the app must start even if migration has issues.
        # Individual request handlers will surface their own specific errors.
        print(f" Database initialization error (non-fatal): {e}")