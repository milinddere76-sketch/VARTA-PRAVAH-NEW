import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

# Import your workflows & activities
from workflows import NewsProductionWorkflow
from activities import fetch_news, generate_script

async def main():
    client = await Client.connect("temporal:7233")

    worker = Worker(
        client,
        task_queue="news-task-queue",
        workflows=[NewsProductionWorkflow],
        activities=[fetch_news, generate_script],
    )

    print("✅ Worker started...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())