import asyncio
from datetime import timedelta, datetime
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec, ScheduleRange, ScheduleCalendarSpec
from .workflows import MasterBulletinWorkflow, BreakingNewsWorkflow
import os

async def setup_schedules(client: Client, channel_id: int, stream_key: str, anchor_ids: list[int]):
    """
    Sets up the 5 daily bulletins and the breaking news checker.
    """
    
    # 1. Breaking News Schedule (Every 3 minutes)
    try:
        await client.create_schedule(
            f"breaking-news-ch{channel_id}",
            Schedule(
                action=ScheduleActionStartWorkflow(
                    BreakingNewsWorkflow.run,
                    {
                        "channel_id": channel_id,
                        "stream_key": stream_key,
                        "anchor_ids": anchor_ids
                    },
                    id=f"breaking-news-ch{channel_id}",
                    task_queue="news-task-queue",
                ),
                spec=ScheduleSpec(
                    intervals=[ScheduleIntervalSpec(every=timedelta(minutes=3))]
                ),
            ),
        )
        print(f"✅ Breaking News Schedule for CH{channel_id} registered.")
    except Exception as e:
        print(f"Breaking News Schedule exists or error: {e}")

    # 2. Daily Bulletins Schedule
    # Scheduled Times: 6:00, 12:00, 18:00, 21:00, 23:00
    bulletin_times = [
        (6, 0, "Morning"),
        (12, 0, "Afternoon"),
        (18, 0, "Evening"),
        (21, 0, "PrimeTime"),
        (23, 0, "Night")
    ]
    
    for hour, minute, b_type in bulletin_times:
        schedule_id = f"bulletin-{b_type}-ch{channel_id}"
        try:
            await client.create_schedule(
                schedule_id,
                Schedule(
                    action=ScheduleActionStartWorkflow(
                        MasterBulletinWorkflow.run,
                        {
                            "channel_id": channel_id,
                            "stream_key": stream_key,
                            "language": "Marathi",
                            "bulletin_type": b_type,
                            "anchor_ids": anchor_ids
                        },
                        id=f"workflow-{schedule_id}",
                        task_queue="news-task-queue",
                    ),
                    spec=ScheduleSpec(
                        calendars=[
                            ScheduleCalendarSpec(
                                hour=[hour],
                                minute=[minute],
                                comment=f"Daily {b_type} Bulletin"
                            )
                        ]
                    ),
                ),
            )
            print(f"✅ Bulletin Schedule '{b_type}' for CH{channel_id} registered.")
        except Exception as e:
            print(f"Bulletin Schedule '{b_type}' exists or error: {e}")

if __name__ == "__main__":
    # For manual testing
    import temporal_utils
    async def run():
        client = await temporal_utils.get_temporal_client()
        await setup_schedules(client, 1, os.getenv("YOUTUBE_STREAM_KEY", ""), [1, 2])
    
    asyncio.run(run())
