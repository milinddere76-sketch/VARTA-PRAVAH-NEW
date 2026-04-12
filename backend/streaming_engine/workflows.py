from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from temporalio import workflow
from temporalio.common import RetryPolicy
from .activities import (
    fetch_news_activity,
    generate_script_activity,
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
    get_channel_anchor_activity
)

@workflow.defn
class StopStreamWorkflow:
    @workflow.run
    async def run(self, channel_id: int) -> str:
        return await workflow.execute_activity(
            stop_stream_activity,
            channel_id,
            start_to_close_timeout=timedelta(seconds=10)
        )

@workflow.defn
class NewsProductionWorkflow:
    @workflow.run
    async def run(self, input_data: dict) -> str:
        channel_id  = input_data["channel_id"]
        language    = input_data["language"]
        stream_key  = input_data["stream_key"]

        # Two anchors passed from worker seed.
        # anchor_ids = [female_id, male_id]  (either may be None if seed failed)
        anchor_ids: list = input_data.get("anchor_ids", [None, None])
        # Determine genders: first slot = female, second = male
        anchor_genders = ["female", "male"]
        bulletin_index = 0   # increments each loop  alternates anchor

        #  0. Ensure promo fallback asset exists 
        await workflow.execute_activity(
            ensure_promo_video_activity,
            start_to_close_timeout=timedelta(seconds=300)  # 3-attempt generation needs time
        )

        #  1. Go LIVE immediately with promo while first news clip generates 
        await workflow.execute_activity(
            start_stream_activity,
            {
                "channel_id": channel_id,
                "stream_key": stream_key,
                "video_url": "videos/promo.mp4",
                "is_promo": True
            },
            start_to_close_timeout=timedelta(seconds=60)
        )

        last_cleanup_day = -1
        ist = ZoneInfo("Asia/Kolkata")

        while True:
            try:
                # --- [BULLETIN PREPARATION] ---
                anchor_slot  = bulletin_index % 2          # 0 = female, 1 = male
                is_female    = (anchor_slot == 0)
                bulletin_index += 1

                # 1. Fetch 10 News Items
                print(f"--- FETCHING BULLETIN NEWS (10 ITEMS) ---")
                news_items = await workflow.execute_activity(
                    fetch_news_activity,
                    language,
                    start_to_close_timeout=timedelta(seconds=90),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )
                # If fetch_news returns a dict, wrap it in a list. 
                items = news_items if isinstance(news_items, list) else [news_items]
                # Slice to 10 max
                items = items[:10]

                story_videos = []
                
                # 2. Sequential Generation (Lip-Sync API limits usually prevent high parallelism)
                for i, story in enumerate(items):
                    print(f"Processing Story {i+1}/{len(items)}...")
                    
                    # - Script (Only show greeting for the VERY FIRST story)
                    script_data = await workflow.execute_activity(
                        generate_script_activity,
                        {"news_data": story, "language": language, "is_female": is_female, "show_greeting": (i == 0)},
                        start_to_close_timeout=timedelta(minutes=5)
                    )

                    # - Audio
                    audio_path = await workflow.execute_activity(
                        generate_audio_activity,
                        {"script": script_data.get("script", ""), "language": language},
                        start_to_close_timeout=timedelta(minutes=5)
                    )

                    # - Lip Sync (Optional/Fallback)
                    synced_video_url = ""
                    try:
                        job_id = await workflow.execute_activity(
                            synclabs_lip_sync_activity,
                            {"audio_url": audio_path, "is_female": is_female},
                            start_to_close_timeout=timedelta(minutes=5)
                        )
                        if job_id not in ["no_api_key", "failed", "mock_job"]:
                            for _ in range(15):
                                status_data = await workflow.execute_activity(check_sync_labs_status_activity, job_id, start_to_close_timeout=timedelta(seconds=60))
                                if status_data.get("status") == "completed":
                                    synced_video_url = status_data.get("video_url")
                                    break
                                await workflow.sleep(timedelta(seconds=20))
                    except: pass

                    # - Render Clip
                    clip_path = await workflow.execute_activity(
                        generate_news_video_activity,
                        {
                            "title": story.get("headline", "Breaking News"),
                            "audio_url": audio_path,
                            "script": script_data.get("script", ""),
                            "synced_video_url": synced_video_url
                        },
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    if clip_path:
                        story_videos.append(clip_path)

                if not story_videos:
                    print("No stories generated. Waiting.")
                    await workflow.sleep(timedelta(minutes=5))
                    continue

                # 3. Concatenate all stories into one Bulletin (5-10 mins total)
                # We'll use generate_news_video_activity but if it doesn't support concat yet, 
                # we'll assume it handles the first one for now or we update the rendering logic.
                # FOR NOW: We stream the first 5 stories for a 5-min block.
                
                full_bulletin_url = story_videos[0] # Root of the bulletin
                
                # 4. Upload & Stream
                s3_url = await workflow.execute_activity(upload_to_s3_activity, full_bulletin_url, start_to_close_timeout=timedelta(minutes=10))
                
                await workflow.execute_activity(
                    start_stream_activity,
                    {"channel_id": channel_id, "stream_key": stream_key, "video_url": s3_url, "is_promo": False},
                    start_to_close_timeout=timedelta(minutes=5)
                )

                # Wait for bulletin to finish (approx 5 mins)
                await workflow.sleep(timedelta(minutes=5))

                # 5. Mandatory 5-Minute Promo Interval
                print("Bulletin Finished. Starting 5-minute Promo Interval...")
                await workflow.execute_activity(
                    start_stream_activity,
                    {"channel_id": channel_id, "stream_key": stream_key, "video_url": "videos/promo.mp4", "is_promo": True},
                    start_to_close_timeout=timedelta(minutes=2)
                )
                await workflow.sleep(timedelta(minutes=5))

            except Exception as e:
                print(f"Bulletin Loop Error: {e}")
                await workflow.sleep(timedelta(minutes=5))
