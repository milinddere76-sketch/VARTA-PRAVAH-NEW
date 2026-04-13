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

async def get_temporal_client(retries: int = 20, delay: int = 5) -> Client:
    """
    Robust Temporal connection with retry (important for Docker startup)
    """
    # Try temporal service name (Docker) then localhost (Local Dev)
    temporal_address = os.getenv("TEMPORAL_ADDRESS")
    if not temporal_address:
        temporal_address = "temporal:7233"

    for attempt in range(retries):
        current_target = temporal_address if attempt % 2 == 0 else "localhost:7233"
        try:
            print(f"Connecting to Temporal ({current_target})... Attempt {attempt+1}/{retries}")
            # Increased timeout to 60s to handle 4GB RAM startup spikes
            client = await asyncio.wait_for(Client.connect(current_target), timeout=60.0)
            print(f"Connected to Temporal successfully via {current_target}")
            return client

        except Exception as e:
            last_error = e
            print(f"Temporal connection failed on {current_target}: {e}")
            await asyncio.sleep(delay)

    raise RuntimeError(f"Unable to connect to Temporal after {retries} attempts: {last_error}")


    raise RuntimeError(f"Unable to connect to Temporal after {retries} attempts: {last_error}")