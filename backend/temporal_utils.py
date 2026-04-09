import os
from dotenv import load_dotenv
from temporalio.client import Client

# Load environment variables from backend/.env during local and container execution
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

async def get_temporal_client():
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    if not temporal_address:
        raise ValueError("TEMPORAL_ADDRESS must be set to connect to Temporal")
    return await Client.connect(temporal_address)
