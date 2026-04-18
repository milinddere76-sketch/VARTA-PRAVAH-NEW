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
            now = workflow.now().replace(tzinfo=ZoneInfo("Asia/Kolkata"))
            
            # Preparation Window: 15 minutes before air time (5, 12, 17, 20, 23)
            # This triggers at 4:45, 11:45, 16:45, 19:45, 22:45
            if now.minute == 45: 
                slot_type = self.get_slot_name(now.hour)
                if slot_type:
                    anchor_type = "female" if self._is_female else "male"
                    print(f"🎬 [SCHEDULER] Triggering {slot_type} Bulletin with {anchor_type.upper()} anchor.")
                    
                    await self.generate(slot_type, anchor_type)
                    
                    # Flip for next slot
                    self._is_female = not self._is_female
            
            await workflow.sleep(timedelta(minutes=1))

    def get_slot_name(self, hour):
        slots = {4: "morning", 11: "afternoon", 16: "evening", 19: "prime", 22: "night"}
        return slots.get(hour)

    async def generate(self, bulletin_type, anchor_type):
        return await workflow.execute_activity(
            generate_news_video_activity,
            (bulletin_type, anchor_type),
            start_to_close_timeout=timedelta(minutes=15)
        )

@workflow.defn
class StopStreamWorkflow:
    @workflow.run
    async def run(self, channel_id: int) -> str:
        # Simplified stop logic
        return "Stream Stop Requested"
