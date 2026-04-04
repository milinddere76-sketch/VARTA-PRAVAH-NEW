import asyncio
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
    for i in range(12):
        try:
            client = await Client.connect("localhost:7233")
            print("Successfully connected to Temporal!")
            break
        except Exception as e:
            print(f"Waiting for Temporal to start... (Attempt {i+1}/12)")
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
