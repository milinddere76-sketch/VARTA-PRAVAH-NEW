import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner
from .workflows import NewsProductionWorkflow
from .activities import (
    fetch_news_activity,
    generate_script_activity,
    synclabs_lip_sync_activity,
    check_sync_labs_status_activity,
    upload_to_s3_activity,
    start_stream_activity
)

async def main():
    from dotenv import load_dotenv
    load_dotenv()
    # Retry loop to wait for Temporal to be ready
    client = None
    # Use TEMPORAL_ADDRESS (standard) or TEMPORAL_HOST (custom) or Docker dns
    temporal_host = os.getenv("TEMPORAL_ADDRESS") or os.getenv("TEMPORAL_HOST") or "temporal:7233"
    
    for i in range(24): # Double the retry count
        try:
            client = await Client.connect(temporal_host)
            print(f"Successfully connected to Temporal on {temporal_host}!")
            break
        except Exception as e:
            print(f"Waiting for Temporal at {temporal_host}... (Attempt {i+1}/24)")
            await asyncio.sleep(10)
    
    if not client:
        print("Failed to connect to Temporal after several attempts.")
        return
    
    worker = Worker(
        client,
        task_queue="news-task-queue",
        workflows=[NewsProductionWorkflow],
        activities=[
            fetch_news_activity,
            generate_script_activity,
            synclabs_lip_sync_activity,
            check_sync_labs_status_activity,
            upload_to_s3_activity,
            start_stream_activity
        ],
        workflow_runner=UnsandboxedWorkflowRunner()
    )
    print("Worker is running...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
