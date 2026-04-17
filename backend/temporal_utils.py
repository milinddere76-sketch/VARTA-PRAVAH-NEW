import os
import asyncio
from dotenv import load_dotenv
from temporalio.client import Client

# ---------------------------
# Load environment variables
# ---------------------------

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

async def get_temporal_client() -> Client:
    """Consolidated direct connection with retry loop."""
    addr = os.getenv("TEMPORAL_ADDRESS", "temporal:7233")
    print(f"🧠 [BRAIN] Connecting to {addr}...")
    
    # Simple, fast retry for Docker connectivity
    for i in range(12): # Try for 1 minute
        try:
            client = await Client.connect(addr)
            print("✅ [BRAIN] Synchronized!")
            return client
        except Exception as e:
            print(f"⏳ [BRAIN] Handshake pending ({i+1}/12): {e}")
            await asyncio.sleep(5)
    
    # Final fallback to raw service name if address env fails
    try:
        return await Client.connect("temporal:7233")
    except:
        raise ConnectionError(f"Could not connect to Temporal at {addr}")