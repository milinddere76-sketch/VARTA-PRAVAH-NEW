import os
import asyncio
import socket
from temporalio.client import Client
from temporalio.service import RPCError

def is_port_open(host_port, timeout=0.5):
    """Quick socket probe to see if a port is alive without waiting for SDK timeouts."""
    try:
        host, port = host_port.split(':')
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except:
        return False

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
        print(f"📡 Speed Probing Temporal at {host}...")
        if not is_port_open(host):
            print(f"⏩ Skipping {host} (Port closed/Unreachable)")
            continue

        for i in range(2): # Quick 2-time retry for each responsive host
            try:
                print(f"🔌 Connecting to Temporal on {host}...")
                client = await Client.connect(host)
                print(f"✅ Connected to Temporal on {host}!")
                return client
            except Exception as e:
                print(f"❌ Connection to {host} failed: {str(e)[:50]}")
                await asyncio.sleep(0.5)
            
    raise ConnectionError(f"Critical: Failed to connect to Temporal after probing {len(host_list)} addresses. Ensure Temporal container is healthy.")
