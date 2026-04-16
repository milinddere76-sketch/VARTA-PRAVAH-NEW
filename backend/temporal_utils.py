import os
import asyncio
from dotenv import load_dotenv
from temporalio.client import Client

# ---------------------------
# Load environment variables
# ---------------------------

# Try multiple locations (works in Docker + local)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

env_paths = [
    os.path.join(BASE_DIR, ".env"),
    os.path.join(BASE_DIR, "../.env"),
    "/app/.env"
]

for path in env_paths:
    if os.path.exists(path):
        load_dotenv(dotenv_path=path)
        break


# ---------------------------
# Temporal Client Connector
# ---------------------------

async def get_temporal_client(retries: int = 40, delay: int = 15) -> Client:
    """
    Robust Temporal connection with retry.
    40 retries x 15s = 10 minutes max wait.
    This is necessary because temporalio/auto-setup takes several minutes
    to initialize the database schema before accepting gRPC connections.
    """
    # Robust Discovery Array
    search_paths = [
        os.getenv("TEMPORAL_ADDRESS", "temporal:7233"),
        "temporal:7233",
        "localhost:7233",
        "127.0.0.1:7233"
    ]

    for attempt in range(retries):
        for addr in search_paths:
            try:
                print(f"Connecting to Temporal ({addr})... Attempt {attempt+1}/{retries}")
                client = await asyncio.wait_for(Client.connect(addr), timeout=2.0)
                print(f"✅ Connected to Temporal successfully via {addr}")
                return client
            except: continue
            
        print(f"⏳ No Brain found yet. Retrying in {delay}s...")
        await asyncio.sleep(delay)

    raise RuntimeError(f"Unable to connect to Temporal after {retries} attempts")