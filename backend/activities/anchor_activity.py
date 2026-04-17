from temporalio import activity
from anchor import get_next_anchor

@activity.defn(name="get_anchor")
async def get_anchor_activity() -> str:
    """
    Temporal activity to safely retrieve the next anchor 
    from the persistent state manager.
    """
    return get_next_anchor()
