import asyncio
import os
from temporalio.client import Client

async def main():
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "temporal:7233")
    print(f"🔄 Connecting to Temporal at {temporal_address}...")
    
    try:
        client = await Client.connect(temporal_address)
        
        # List all running workflows
        print("🔍 Searching for stuck workflows...")
        async for workflow in client.list_workflows('ExecutionStatus="Running"'):
            print(f"🛑 Terminating: {workflow.id} (RunID: {workflow.run_id})")
            handle = client.get_workflow_handle(workflow.id, run_id=workflow.run_id)
            await handle.terminate(reason="Manual reset via diagnostic script")
            
        print("✅ Cleanup complete. All stuck workflows terminated.")
    except Exception as e:
        print(f"❌ Failed to cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(main())
