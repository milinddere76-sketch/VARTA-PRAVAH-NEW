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

async def get_temporal_client(retries: int = 10, delay: int = 5) -> Client:
    """
    Robust Temporal connection with retry (important for Docker startup)
    """
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "temporal:7233")

    if not temporal_address:
        raise ValueError("TEMPORAL_ADDRESS must be set")

    last_error = None

    for attempt in range(retries):
        try:
            print(f"Connecting to Temporal ({temporal_address})... Attempt {attempt+1}/{retries}")
            client = await Client.connect(temporal_address)
            print("✅ Connected to Temporal successfully")
            return client

        except Exception as e:
            last_error = e
            print(f"❌ Temporal connection failed: {e}")
            await asyncio.sleep(delay)

    raise RuntimeError(f"Unable to connect to Temporal after {retries} attempts: {last_error}")