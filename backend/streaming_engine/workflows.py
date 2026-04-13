import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
import os

# Import activities
with workflow.unsafe.imports_passed_through():
    from .activities import (
        fetch_news_activity,
        generate_script_activity,
        generate_headlines_activity,
        generate_closing_activity,
        generate_audio_activity,
        generate_news_video_activity,
        synclabs_lip_sync_activity,
        check_sync_labs_status_activity,
        upload_to_s3_activity,
        start_stream_activity,
        ensure_promo_video_activity,
        ensure_premium_promo_activity,
        stop_stream_activity,
        check_scheduled_ads_activity,
        cleanup_old_videos_activity,
        merge_videos_activity,
        stitch_bulletin_activity,
        find_latest_bulletin_activity
    )


@workflow.defn
class StopStreamWorkflow:
    @workflow.run
    async def run(self, channel_id: int) -> str:
        return await workflow.execute_activity(
            stop_stream_activity,
            channel_id,
            start_to_close_timeout=timedelta(minutes=1)
        )

@workflow.defn
class NewsBatchWorkflow:
    """
    SEQUENTIAL generation of all bulletins for the cycle (Morning/Evening).
    Triggered at 05:00 AM and 05:00 PM IST.
    """
    @workflow.run
    async def run(self, data: dict) -> str:
        channel_id = data["channel_id"]
        cycle = data.get("cycle", "Morning") # "Morning" or "Evening"
        language = data.get("language", "Marathi")
        anchor_ids = data.get("anchor_ids", [1, 2])
        
        # 1. Fetch News (Batch of 25-30)
        items = await workflow.execute_activity(
            fetch_news_activity, 
            language, 
            start_to_close_timeout=timedelta(minutes=5)
        )
        if not items: return "No news found for batch."

        # 2. Generate Headlines (Female anchor for consistency)
        headlines_data = await workflow.execute_activity(
            generate_headlines_activity,
            {"news_items": items[:5], "is_female": True},
            start_to_close_timeout=timedelta(minutes=5)
        )
        headlines_audio = await workflow.execute_activity(
            generate_audio_activity,
            {"script": headlines_data["script"], "is_female": True},
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        top_headlines_text = [n['headline'] for n in items[:5]]
        
        headlines_video = await workflow.execute_activity(
            generate_news_video_activity,
            {
                "audio_url": headlines_audio, 
                "title": "मुख्य बातम्या", 
                "is_female": True,
                "top_headlines": top_headlines_text
            },
            start_to_close_timeout=timedelta(minutes=10)
        )

        # 3. Generate individual story videos SEQUENTIALLY
        story_videos = []
        for i, item in enumerate(items):
            # Alternate Male/Female
            is_f = (i % 2 == 0)
            a_id = anchor_ids[0] if is_f else anchor_ids[1]

            script = await workflow.execute_activity(
                generate_script_activity,
                {"news_data": item, "language": language, "is_female": is_f, "show_greeting": (i==0)},
                start_to_close_timeout=timedelta(minutes=2)
            )
            audio = await workflow.execute_activity(
                generate_audio_activity,
                {"script": script["script"], "is_female": is_f},
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            # (Lip sync skipped for batch speed/resource unless requested, using static for now)
            v_path = await workflow.execute_activity(
                generate_news_video_activity,
                {
                    "audio_url": audio,
                    "title": item["headline"],
                    "is_female": is_f,
                    "top_headlines": top_headlines_text
                },
                start_to_close_timeout=timedelta(minutes=10)
            )
            if v_path: story_videos.append(v_path)

        # 4. Assemble the specific bulletins for the cycle
        common_data = {
            "channel_id": channel_id,
            "headlines_path": headlines_video,
            "story_paths": story_videos,
            "promo_path": f"videos/promo_ch{channel_id}.mp4",
            "intro_path": "assets/intro.mp4"
        }

        if cycle == "Morning":
            # Morning Headlines (30 min)
            await workflow.execute_activity(
                stitch_bulletin_activity, 
                {**common_data, "target_minutes": 30, "output_name": "morning_headlines"},
                start_to_close_timeout=timedelta(minutes=20)
            )
            # Morning Bulletin (120 min)
            await workflow.execute_activity(
                stitch_bulletin_activity, 
                {**common_data, "target_minutes": 120, "output_name": "morning_bulletin"},
                start_to_close_timeout=timedelta(minutes=30)
            )
            # Afternoon Bulletin (120 min)
            await workflow.execute_activity(
                stitch_bulletin_activity, 
                {**common_data, "target_minutes": 120, "output_name": "afternoon_bulletin"},
                start_to_close_timeout=timedelta(minutes=30)
            )
        else:
            # Evening Cycle
            await workflow.execute_activity(
                stitch_bulletin_activity, 
                {**common_data, "target_minutes": 30, "output_name": "evening_headlines"},
                start_to_close_timeout=timedelta(minutes=20)
            )
            await workflow.execute_activity(
                stitch_bulletin_activity, 
                {**common_data, "target_minutes": 120, "output_name": "prime_time"},
                start_to_close_timeout=timedelta(minutes=30)
            )
            await workflow.execute_activity(
                stitch_bulletin_activity, 
                {**common_data, "target_minutes": 120, "output_name": "night_bulletin"},
                start_to_close_timeout=timedelta(minutes=30)
            )

        return f"{cycle} Batch Generation Completed."

@workflow.defn
class MasterBulletinWorkflow:
    """
    Slot Broadcaster: Triggered at specific times to switch the live stream.
    Used for 05:30, 06:00, 08:00 etc.
    """
    @workflow.run
    async def run(self, data: dict) -> str:
        channel_id = data["channel_id"]
        stream_key = data["stream_key"]
        file_prefix = data.get("file_prefix", "morning_bulletin") # morning_headlines, morning_bulletin, etc.
        
        # 1. Find the latest file matching the prefix
        # Note: Broadcaster should look for 'bulletin_batch_*.mp4' or specific named files
        # For simplicity, we'll implement find_latest_by_prefix_activity or just use what we have
        latest_path = await workflow.execute_activity(
            find_latest_bulletin_activity,
            channel_id,
            start_to_close_timeout=timedelta(minutes=1)
        )
        
        if not latest_path:
            print(f"--- [FALLBACK] No bulletin for {file_prefix}. Falling back to promo.")
            latest_path = f"videos/promo_ch{channel_id}.mp4"

        # 2. Start Telecast
        await workflow.execute_activity(
            start_stream_activity,
            {"channel_id": channel_id, "stream_key": stream_key, "video_url": latest_path, "is_promo": True if "promo" in latest_path else False},
            start_to_close_timeout=timedelta(minutes=5)
        )

        
        return f"Broadcasting {file_prefix} started."


@workflow.defn
class BreakingNewsWorkflow:
    """
    Checks for high-priority news every 5 minutes and enqueues (seamlessly)
    if found.
    """
    @workflow.run
    async def run(self, data: dict):
        channel_id = data["channel_id"]
        stream_key = data["stream_key"]
        anchor_ids = data.get("anchor_ids", [1, 2])
        
        while True:
            # 1. Check for fresh breaking news
            news = await workflow.execute_activity(
                fetch_news_activity, 
                "Marathi",
                start_to_close_timeout=timedelta(minutes=1)
            )
            
            # Filter for true 'BREAKING' priority items
            breaking_items = [n for n in news if n.get("category") == "BREAKING"][:1]
            
            if breaking_items:
                item = breaking_items[0]
                
                # Use current top headlines for the ticker context
                top_headlines = [n['headline'] for n in news[:5]]
                
                # 2. Generate Instant Clip (Sequential)
                script_data = await workflow.execute_activity(
                    generate_script_activity, 
                    {"news_data": item, "language": "Marathi", "is_female": True}, 
                    start_to_close_timeout=timedelta(minutes=2)
                )
                audio_path = await workflow.execute_activity(
                    generate_audio_activity, 
                    {"script": script_data["script"], "is_female": True}, 
                    start_to_close_timeout=timedelta(minutes=2)
                )
                video_path = await workflow.execute_activity(
                    generate_news_video_activity, 
                    {
                        "audio_url": audio_path, 
                        "title": item.get("headline", "BREAKING NEWS"), 
                        "is_female": True,
                        "top_headlines": top_headlines
                    }, 
                    start_to_close_timeout=timedelta(minutes=5)
                )
                
                # 3. Enqueue (Non-Interrupting)
                if video_path:
                    await workflow.execute_activity(
                        start_stream_activity,
                        {"channel_id": channel_id, "stream_key": stream_key, "video_url": video_path, "is_priority": True},
                        start_to_close_timeout=timedelta(minutes=5)
                    )
            
            # Wait 5 minutes for next check as per core rule
            await workflow.sleep(timedelta(minutes=5))


@workflow.defn
class NewsProductionWorkflow:
    """
    Main long-running workflow for 24/7 news production (Deprecated by MasterBulletin but kept for compatibility)
    """
    @workflow.run
    async def run(self, data: dict) -> str:
        # Relies on the previous logic...
        pass

@workflow.defn
class StartImmediateStreamWorkflow:
    @workflow.run
    async def run(self, data: dict):
        channel_id = data.get("channel_id", 1)
        
        # 1. Ensure the PREMIUM promo exists
        await workflow.execute_activity(
            ensure_premium_promo_activity,
            start_to_close_timeout=timedelta(minutes=5)
        )

        # 2. Ensure the channel-specific synced version exists
        await workflow.execute_activity(
            ensure_promo_video_activity,
            channel_id,
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        # 2. Execute the stream start
        await workflow.execute_activity(
            start_stream_activity,
            data,
            start_to_close_timeout=timedelta(minutes=5)
        )
        return "Immediate stream started"
