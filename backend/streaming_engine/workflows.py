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
class MasterBulletinWorkflow:
    """
    Handles the 60-minute scheduled bulletins (Morning, Afternoon, etc.)
    with alternating anchors and seamless structure.
    """
    @workflow.run
    async def run(self, data: dict) -> str:

        channel_id = data["channel_id"]
        stream_key = data["stream_key"]
        language = data["language"]
        bulletin_type = data.get("bulletin_type", "Regular")
        anchor_ids = data.get("anchor_ids", []) # [female_id, male_id]
        
        from datetime import datetime, timedelta
        import zoneinfo
        
        # Current time in IST for slot checking
        now_ist = datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
        
        # Calculate target hour (the next hour after the :45 trigger)
        # If triggered at 5:45, target is 6:00
        target_time_ist = now_ist.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        target_hour = target_time_ist.hour
        
        # FRESH_HOURS = [6, 12, 18, 21, 23]
        is_fresh_slot = target_hour in [6, 12, 18, 21, 23] or bulletin_type != "Regular"
        
        if not is_fresh_slot:
            print(f"--- [REPEAT MODE] Target Hour {target_hour} is not a fresh slot. Searching for latest bulletin. ---")
            latest_path = await workflow.execute_activity(
                find_latest_bulletin_activity,
                channel_id,
                start_to_close_timeout=timedelta(minutes=1)
            )
            if latest_path and os.path.exists(latest_path):
                print(f"--- [REPEAT] Found latest bulletin: {latest_path}. Waiting for Top of Hour. ---")
                
                # Wait until the target hour starts
                now_utc = workflow.now()
                # Target time in UTC (IST-5.5)
                wait_duration = target_time_ist - now_ist
                if wait_duration.total_seconds() > 0:
                    await workflow.sleep(wait_duration)
                
                print(f"--- [REPEAT] Streaming {target_hour}:00 Bulletin now. ---")
                await workflow.execute_activity(
                    start_stream_activity,
                    {"channel_id": channel_id, "stream_key": stream_key, "video_url": latest_path, "is_promo": False},
                    start_to_close_timeout=timedelta(minutes=5)
                )
                await workflow.sleep(timedelta(minutes=55)) # Telecast duration
                return f"Bulletin Repeat (Hour {target_hour}) completed."
            else:
                print(f"--- [REPEAT] No previous bulletin found. Forcing fresh generation for {target_hour}:00. ---")


        print(f"--- STARTING MASTER BULLETIN: {bulletin_type} ---")
        
        # 1. Fetch 20 News Items for a 60min loop
        items = await workflow.execute_activity(
            fetch_news_activity, 
            language, 
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        if not items:
            return "No news found for bulletin."

        # 2. Generate Intro & Headlines
        is_female = True # Headlines always female for consistency
        headlines_data = await workflow.execute_activity(
            generate_headlines_activity,
            {"news_items": items[:5], "is_female": is_female},
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        headlines_audio = await workflow.execute_activity(
            generate_audio_activity,
            {"script": headlines_data["script"], "is_female": is_female},
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        headlines_path = await workflow.execute_activity(
            generate_news_video_activity,
            {"audio_url": headlines_audio, "title": f"{bulletin_type} Headlines", "is_female": is_female},
            start_to_close_timeout=timedelta(minutes=5)
        )


        # 3. Generate Individual Stories with Alternating Anchors
        story_videos = []
        if headlines_path:
            story_videos.append(headlines_path)

        for i, item in enumerate(items):
            # Alternating gender: Even = Female, Odd = Male
            current_is_female = (i % 2 == 0)
            current_anchor_id = anchor_ids[0] if current_is_female else (anchor_ids[1] if len(anchor_ids) > 1 else anchor_ids[0])
            
            # Generate Script
            script_data = await workflow.execute_activity(
                generate_script_activity,
                {"news_data": item, "language": language, "is_female": current_is_female},
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            # Generate Audio
            audio_path = await workflow.execute_activity(
                generate_audio_activity,
                {"script": script_data["script"], "anchor_id": current_anchor_id, "is_female": current_is_female},
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            # Generate Video
            video_path = await workflow.execute_activity(
                generate_news_video_activity,
                {
                    "audio_url": audio_path, 
                    "title": item["headline"], 
                    "anchor_id": current_anchor_id, 
                    "is_female": current_is_female
                },
                start_to_close_timeout=timedelta(minutes=10)
            )
            if video_path:
                story_videos.append(video_path)



        # 4. Stitch into 60-minute Bulletin
        full_bulletin_path = await workflow.execute_activity(
            stitch_bulletin_activity,
            {
                "channel_id": channel_id,
                "headlines_path": headlines_path,
                "story_paths": story_videos,
                "promo_path": f"videos/promo_ch{channel_id}.mp4",
                "intro_path": "assets/intro.mp4"
            },
            start_to_close_timeout=timedelta(minutes=15)
        )


        # 5. Start Telecast
        print(f"--- [FRESH] Bulletin Ready. Waiting for Top of Hour ({target_hour}:00). ---")
        now_ist = datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
        wait_duration = target_time_ist - now_ist
        if wait_duration.total_seconds() > 0:
            await workflow.sleep(wait_duration)

        print(f"--- [FRESH] Starting {target_hour}:00 Telecast now. ---")
        await workflow.execute_activity(
            start_stream_activity,
            {"channel_id": channel_id, "stream_key": stream_key, "video_url": full_bulletin_path, "is_promo": False},
            start_to_close_timeout=timedelta(minutes=5)
        )

        
        # Wait for 1 hour telecast duration (or until next schedule)
        await workflow.sleep(timedelta(hours=1))
        
        return f"Bulletin {bulletin_type} completed."

@workflow.defn
class BreakingNewsWorkflow:
    """
    Checks for high-priority news every 2-5 minutes and interrupts (seamlessly)
    if found.
    """
    @workflow.run
    async def run(self, data: dict):
        channel_id = data["channel_id"]
        stream_key = data["stream_key"]
        anchor_ids = data.get("anchor_ids", [])
        
        while True:
            # 1. Check for fresh breaking news
            news = await workflow.execute_activity(
                fetch_news_activity, 
                "Marathi", # Hardcoded for now per requirements
                start_to_close_timeout=timedelta(minutes=1)
            )
            
            # Filter for true 'BREAKING' priority items
            breaking_items = [n for n in news if n.get("category") == "BREAKING"]
            
            if breaking_items:
                item = breaking_items[0]
                # 2. Generate Instant Clip
                script_data = await workflow.execute_activity(
                    generate_script_activity, 
                    {"news_data": item, "language": "Marathi"}, 
                    start_to_close_timeout=timedelta(minutes=1)
                )
                audio_path = await workflow.execute_activity(
                    generate_audio_activity, 
                    {"script": script_data["script"], "anchor_id": anchor_ids[0]}, 
                    start_to_close_timeout=timedelta(minutes=1)
                )
                video_path = await workflow.execute_activity(
                    generate_news_video_activity, 
                    {
                        "audio_url": audio_path, 
                        "title": item.get("headline", "BREAKING NEWS"), 
                        "anchor_id": anchor_ids[0]
                    }, 
                    start_to_close_timeout=timedelta(minutes=2)
                )
                
                # 3. Interrupted (Seamless): Signal the Streamer
                if video_path:
                    await workflow.execute_activity(
                        start_stream_activity,
                        {"channel_id": channel_id, "stream_key": stream_key, "video_url": video_path, "is_priority": True},
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                # To be TRULY seamless, we'd need a more complex Streamer.
                # For now, we follow the "at next possible moment" by updating the playlist.
                await workflow.execute_activity(
                    start_stream_activity,
                    {"channel_id": channel_id, "stream_key": stream_key, "video_url": video, "is_promo": False},
                    start_to_close_timeout=timedelta(minutes=1)
                )
                
                # Wait for breaking news duration (approx 90s)
                await workflow.sleep(timedelta(seconds=90))
            
            await workflow.sleep(timedelta(minutes=3))

@workflow.defn
class NewsProductionWorkflow:
    """
    Main long-running workflow for 24/7 news production (Deprecated by MasterBulletin but kept for compatibility)
    """
    @workflow.run
    async def run(self, data: dict) -> str:
        # Relies on the previous logic...
        pass
