import asyncio
from datetime import timedelta, datetime
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec, ScheduleRange, ScheduleCalendarSpec
from .workflows import MasterBulletinWorkflow, BreakingNewsWorkflow, NewsBatchWorkflow
import os

async def setup_schedules(client: Client, channel_id: int, stream_key: str, anchor_ids: list[int]):
    """
    Sets up the new 24x7 schedule:
    1. Batch Generation (05:00 AM/PM)
    2. Slot Switch Triggers
    3. 5-min Breaking News Check
    """
    
    # --- 1. Batch Generation Schedules ---
    # Morning Batch (05:00 AM)
    try:
        await client.create_schedule(
            f"batch-gen-morning-ch{channel_id}",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    NewsBatchWorkflow.run,
                    {"channel_id": channel_id, "cycle": "Morning", "anchor_ids": anchor_ids},
                    id=f"batch-morning-ch{channel_id}",
                    task_queue="news-task-queue",
                ),
                spec=ScheduleSpec(calendars=[ScheduleCalendarSpec(hour=5, minute=0)])
            )
        )
    except: pass

    # Evening Batch (05:00 PM)
    try:
        await client.create_schedule(
            f"batch-gen-evening-ch{channel_id}",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    NewsBatchWorkflow.run,
                    {"channel_id": channel_id, "cycle": "Evening", "anchor_ids": anchor_ids},
                    id=f"batch-evening-ch{channel_id}",
                    task_queue="news-task-queue",
                ),
                spec=ScheduleSpec(calendars=[ScheduleCalendarSpec(hour=17, minute=0)])
            )
        )
    except: pass


    # --- 2. Slot Switching Schedules ---
    slots = [
        # Morning Cycle
        (5, 30, "morning_headlines"),
        (6, 0,  "morning_bulletin"),
        (8, 0,  "morning_bulletin"),
        (10, 0, "afternoon_bulletin"),
        (12, 0, "afternoon_bulletin"),
        (14, 0, "morning_bulletin"),
        (16, 0, "afternoon_bulletin"),
        # Evening Cycle
        (17, 30, "evening_headlines"),
        (18, 0,  "prime_time"),
        (19, 0,  "prime_time"),
        (21, 0,  "prime_time"),
        (23, 0,  "night_bulletin"),
        (1, 0,   "night_bulletin"),
        (3, 0,   "night_bulletin"),
    ]

    for h, m, prefix in slots:
        try:
            await client.create_schedule(
                f"slot-{h:02d}{m:02d}-ch{channel_id}",
                Schedule(
                    action=ScheduleActionStartWorkflow(
                        MasterBulletinWorkflow.run,
                        {"channel_id": channel_id, "stream_key": stream_key, "file_prefix": prefix},
                        id=f"switch-{h:02d}{m:02d}-ch{channel_id}",
                        task_queue="news-task-queue",
                    ),
                    spec=ScheduleSpec(calendars=[ScheduleCalendarSpec(hour=h, minute=m)])
                )
            )
        except: pass

    # --- 3. Breaking News Engine (Every 5 mins 24x7) ---
    try:
        await client.create_schedule(
            f"breaking-news-engine-ch{channel_id}",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    BreakingNewsWorkflow.run,
                    {"channel_id": channel_id, "stream_key": stream_key, "anchor_ids": anchor_ids},
                    id=f"breaking-engine-ch{channel_id}",
                    task_queue="news-task-queue",
                ),
                spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(minutes=5))])
            )
        )
    except: pass

    print(f"✅ Full 24x7 Schedule for Channel {channel_id} synchronized.")




if __name__ == "__main__":
    # For manual testing
    import temporal_utils
    async def run():
        client = await temporal_utils.get_temporal_client()
        await setup_schedules(client, 1, os.getenv("YOUTUBE_STREAM_KEY", ""), [1, 2])
    
    asyncio.run(run())
