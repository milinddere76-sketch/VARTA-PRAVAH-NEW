import asyncio
from temporalio.client import Client

async def main():
    try:
        client = await Client.connect("localhost:7233")
        
        ids = ["news-production-auto", "news-production-1", "news-production-master", "breaking-news-monitor"]
        for wid in ids:
            try:
                handle = client.get_workflow_handle(wid)
                await handle.terminate()
                print(f"✅ Terminated workflow: {wid}")
            except Exception as e:
                print(f"ℹ️ Workflow {wid} not found or already terminated")

    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
