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
    start_stream_activity,
    ensure_promo_video_activity
)

async def trigger_auto_start(client: Client):
    channel_id = os.getenv("AUTO_START_CHANNEL_ID", "1")
    language = os.getenv("DEFAULT_LANGUAGE", "mr")
    stream_key = os.getenv("YOUTUBE_STREAM_KEY", "")
    workflow_id = f"news-production-{channel_id}"

    if not stream_key:
        print("Auto-trigger skipped: YOUTUBE_STREAM_KEY is missing.")
        return

    try:
        # Check if already running
        handle = client.get_workflow_handle(workflow_id)
        desc = await handle.describe()
        if desc.status.name == "RUNNING":
            print(f"Workflow {workflow_id} is already running. Skipping auto-trigger.")
            return
    except Exception:
        # Not found or error, proceed to start
        pass

    print(f"Deployment Detected: Auto-triggering News Production for Channel {channel_id} ({language})...")
    try:
        await client.start_workflow(
            NewsProductionWorkflow.run,
            {
                "channel_id": int(channel_id),
                "language": language,
                "stream_key": stream_key
            },
            id=workflow_id,
            task_queue="news-task-queue"
        )
        print(f"Successfully triggered autonomous news for Channel {channel_id}.")
    except Exception as e:
        print(f"Auto-trigger failed: {e}")

async def main():
    from dotenv import load_dotenv
    load_dotenv()
    
    # Use TEMPORAL_ADDRESS (standard) or TEMPORAL_HOST (custom) or Docker dns
    temporal_host = os.getenv("TEMPORAL_ADDRESS") or os.getenv("TEMPORAL_HOST") or "temporal:7233"
    client = None
    
    for i in range(24):
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

    # AUTO-TRIGGER: Start the 24/7 show immediately on boot
    asyncio.create_task(trigger_auto_start(client))
    
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
            start_stream_activity,
            ensure_promo_video_activity
        ],
        workflow_runner=UnsandboxedWorkflowRunner()
    )
    print("Worker is running...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
