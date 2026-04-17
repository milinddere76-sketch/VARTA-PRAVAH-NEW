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
    # 1. Try environment/direct first
    search_paths = [os.getenv("TEMPORAL_ADDRESS", "temporal:7233"), "temporal:7233", "localhost:7233"]
    
    # 2. Add full subnet scan if isolated (Last Resort - The Hunter)
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Scan 172.21.0.x and 172.20.0.x (Coolify defaults)
        prefix = ".".join(local_ip.split(".")[:3])
        for i in range(1, 20): # Scan early arrivals first
            search_paths.append(f"{prefix}.{i}:7233")
    except: pass

    for attempt in range(retries):
        for addr in search_paths:
            try:
                # Fast timeout for scan check
                client = await asyncio.wait_for(Client.connect(addr), timeout=1.0)
                print(f"✅ [HUNTER] Brain found and connected at: {addr}")
                return client
            except: continue
        
        print(f"⏳ [SCAN] No Brain in current subnet ({local_ip[:-1]}*). Retrying {attempt+1}/{retries}...")
        await asyncio.sleep(delay)

    raise RuntimeError(f"Unable to connect to Temporal after {retries} attempts")