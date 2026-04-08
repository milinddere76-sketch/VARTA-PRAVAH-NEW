import os
import asyncio
from temporalio.client import Client
from temporalio.service import RPCError

async def get_temporal_client(max_retries=24, delay=5):
    """
    Service Shield: Connects to Temporal with a silent retry loop.
    Standardizes connection logic between Main API and Workers.
    """
    # 🛰️ Probing all possible addresses for maximum reliability
    addresses_to_try = [
        os.getenv("TEMPORAL_ADDRESS"),
        os.getenv("TEMPORAL_HOST"),
        "temporal:7233",
        "localhost:7233",
        "127.0.0.1:7233",
        # Adding the specific Coolify-generated name as a fallback for this environment
        "temporal-t892o397h64afn1mgn4lndi3-234723919922:7233"
    ]
    
    # Filter out None and empty strings
    host_list = [h for h in addresses_to_try if h]
    
    for host in host_list:
        for i in range(3): # Quick 3-time retry for each host
            try:
                print(f"📡 Probing Temporal at {host}...")
                client = await Client.connect(host)
                print(f"✅ Connected to Temporal on {host}!")
                return client
            except Exception as e:
                print(f"❌ Host {host} failed: {str(e)}")
                await asyncio.sleep(1)
            
    raise ConnectionError(f"Critical: Failed to connect to Temporal after probing {len(host_list)} addresses.")
