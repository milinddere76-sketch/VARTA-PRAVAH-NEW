from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio
from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities
from .activities import (
    generate_news_video_activity
)

@workflow.defn
class NewsSchedulerWorkflow:
    def __init__(self):
        self._is_female = True # Start with Female

    @workflow.run
    async def run(self, channel_id: int):
        while True:
            # Trigger every 15 minutes (00, 15, 30, 45)
            now = workflow.now().replace(tzinfo=ZoneInfo("Asia/Kolkata"))
            
            if now.minute in [0, 15, 30, 45]:
                slot_type = self.get_slot_name(now.hour)
                anchor_type = "female" if self._is_female else "male"
                print(f"🎬 [SCHEDULER] Triggering News Bulletin: {slot_type} with {anchor_type}.")
                
                await workflow.execute_activity(
                    generate_news_video_activity,
                    (slot_type, anchor_type),
                    start_to_close_timeout=timedelta(minutes=15)
                )
                
                # Flip for next slot
                self._is_female = not self._is_female
            
            # Sleep until the next minute
            await workflow.sleep(timedelta(minutes=1))

    def get_slot_name(self, hour):
        slots = {4: "morning", 11: "afternoon", 16: "evening", 19: "prime", 22: "night"}
        return slots.get(hour)

@workflow.defn
class StopStreamWorkflow:
    @workflow.run
    async def run(self, channel_id: int) -> str:
        return "Stream Stop Requested"

@workflow.defn
class CheckBreakingNewsWorkflow:
    @workflow.run
    async def run(self) -> None:
        while True:
            # Monitors the news feed for high-priority flashes
            await workflow.sleep(timedelta(minutes=5))
