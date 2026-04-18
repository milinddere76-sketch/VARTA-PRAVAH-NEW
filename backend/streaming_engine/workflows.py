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
    async def run(self, channel_id: int, immediate: bool = False):
        last_trigger_minute = -1
        
        # 🚀 IMMEDIATE TRIGGER (for Force Start or Reboot)
        if immediate:
            print("🚀 [SCHEDULER] Immediate Production Triggered.")
            now = workflow.now().astimezone(ZoneInfo("Asia/Kolkata"))
            slot_type = self.get_slot_name(now.hour)
            anchor_type = "female" if self._is_female else "male"
            
            await workflow.execute_activity(
                generate_news_video_activity,
                (slot_type, anchor_type),
                start_to_close_timeout=timedelta(minutes=15)
            )
            self._is_female = not self._is_female
            last_trigger_minute = now.minute

        while True:
            # Trigger every 15 minutes (00, 15, 30, 45)
            now = workflow.now().astimezone(ZoneInfo("Asia/Kolkata"))
            
            if now.minute in [0, 15, 30, 45] and now.minute != last_trigger_minute:
                last_trigger_minute = now.minute
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
        if 4 <= hour < 11: return "morning"
        if 11 <= hour < 16: return "afternoon"
        if 16 <= hour < 19: return "evening"
        if 19 <= hour < 22: return "prime"
        return "night"

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
