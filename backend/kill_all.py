import asyncio
import temporal_utils

async def kill_all():
    client = await temporal_utils.get_temporal_client()
    # List all running workflows
    # Using raw string for the query to avoid quoting issues
    query = 'ExecutionStatus="Running"'
    print(f"--- [CLEANUP] Fetching workflows matching: {query} ---")
    
    workflows = client.list_workflows(query)
    count = 0
    async for w in workflows:
        if w.id.startswith("breaking-news-"): # Target the problematic ones
            try:
                handle = client.get_workflow_handle(w.id)
                await handle.terminate(reason="Upgrading news engine architecture")
                count += 1
                print(f"  Terminated: {w.id}")
            except Exception as e:
                print(f"  Failed to terminate {w.id}: {e}")
    
    print(f"--- [CLEANUP] Done. Terminated {count} workflows. ---")

if __name__ == "__main__":
    asyncio.run(kill_all())
