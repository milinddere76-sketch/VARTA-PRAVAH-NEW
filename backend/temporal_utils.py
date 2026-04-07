import os
import asyncio
from temporalio.client import Client

async def get_temporal_client(max_retries=24, delay=10):
    """
    Service Shield: Connects to Temporal with a silent retry loop.
    Standardizes connection logic between Main API and Workers.
    """
    # Prioritize TEMPORAL_ADDRESS (Temporal Standard) -> TEMPORAL_HOST (Legacy)
    temporal_host = os.getenv("TEMPORAL_ADDRESS") or os.getenv("TEMPORAL_HOST") or "temporal:7233"
    
    for i in range(max_retries):
        try:
            client = await Client.connect(temporal_host)
            print(f"✅ Connected to Temporal on {temporal_host}!")
            return client
        except Exception:
            # We print status only in context of the worker's initial boot
            # In the API, we fail gracefully to avoid blocking the main server
            print(f"⏳ Waiting for Temporal Engine... ({i+1}/{max_retries})")
            await asyncio.sleep(delay)
            
    raise ConnectionError(f"Critical: Failed to connect to Temporal at {temporal_host} after {max_retries} attempts.")
