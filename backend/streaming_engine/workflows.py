from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from temporalio import workflow
from temporalio.common import RetryPolicy
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

        anchor_ids: list = input_data.get("anchor_ids", [None, None])
        anchor_genders = ["female", "male"]
        bulletin_index = 0

        await workflow.execute_activity(
            ensure_promo_video_activity,
            channel_id, # Add channel ID to make promo unique
            start_to_close_timeout=timedelta(seconds=300)
        )

        await workflow.execute_activity(
            start_stream_activity,
            {
                "channel_id": channel_id,
                "stream_key": stream_key,
                "video_url": f"videos/promo_ch{channel_id}.mp4",
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
                items = news_items if isinstance(news_items, list) else [news_items]
                items = items[:10]

                # --- NEW: HEADLINES BLOCK (Fast Delivery) ---
                print("--- GENERATING HEADLINES BLOCK ---")
                headlines_data = await workflow.execute_activity(
                    generate_headlines_activity,
                    {"news_items": items, "is_female": is_female},
                    start_to_close_timeout=timedelta(minutes=5)
                )
                headlines_audio = await workflow.execute_activity(
                    generate_audio_activity,
                    {"script": headlines_data["script"], "is_female": is_female},
                    start_to_close_timeout=timedelta(minutes=5)
                )
                headlines_clip = await workflow.execute_activity(
                    generate_news_video_activity,
                    {
                        "title": "HEADLINES",
                        "audio_url": headlines_audio,
                        "script": headlines_data["script"],
                        "is_female": is_female
                    },
                    start_to_close_timeout=timedelta(minutes=5)
                )

                story_videos = [headlines_clip] if headlines_clip else []
                
                # 2. Sequential Generation for Individual Stories
                for i, story in enumerate(items):
                    print(f"Processing Story {i+1}/{len(items)}...")
                    
                    script_data = await workflow.execute_activity(
                        generate_script_activity,
                        {"news_data": story, "language": language, "is_female": is_female, "show_greeting": False},
                        start_to_close_timeout=timedelta(minutes=5)
                    )

                    audio_path = await workflow.execute_activity(
                        generate_audio_activity,
                        {"script": script_data.get("script", ""), "is_female": is_female},
                        start_to_close_timeout=timedelta(minutes=5)
                    )

                    synced_video_url = ""
                    try:
                        job_id = await workflow.execute_activity(
                            synclabs_lip_sync_activity,
                            {"audio_url": audio_path, "is_female": is_female},
                            start_to_close_timeout=timedelta(minutes=5)
                        )
                        if job_id not in ["no_api_key", "failed", "mock_job"]:
                            # Increase polling for longer news segments (up to 10 mins)
                            for _ in range(25):
                                status_data = await workflow.execute_activity(check_sync_labs_status_activity, job_id, start_to_close_timeout=timedelta(seconds=60))
                                if status_data.get("status") == "completed":
                                    synced_video_url = status_data.get("video_url")
                                    break
                                await workflow.sleep(timedelta(seconds=25))
                    except: pass

                    clip_path = await workflow.execute_activity(
                        generate_news_video_activity,
                        {
                            "title": story.get("headline", "Breaking News"),
                            "audio_url": audio_path,
                            "script": script_data.get("script", ""),
                            "synced_video_url": synced_video_url,
                            "is_female": is_female
                        },
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    if clip_path:
                        story_videos.append(clip_path)

                # --- NEW: CLOSING BLOCK ---
                print("--- GENERATING CLOSING BLOCK ---")
                closing_data = await workflow.execute_activity(
                    generate_closing_activity,
                    {"is_female": is_female},
                    start_to_close_timeout=timedelta(minutes=2)
                )
                closing_audio = await workflow.execute_activity(
                    generate_audio_activity,
                    {"script": closing_data["script"], "is_female": is_female},
                    start_to_close_timeout=timedelta(minutes=2)
                )
                closing_clip = await workflow.execute_activity(
                    generate_news_video_activity,
                    {
                        "title": "Closing",
                        "audio_url": closing_audio,
                        "script": closing_data["script"],
                        "is_female": is_female
                    },
                    start_to_close_timeout=timedelta(minutes=5)
                )
                if closing_clip:
                    story_videos.append(closing_clip)

                if not story_videos:
                    print("No stories generated.")
                    await workflow.sleep(timedelta(minutes=5))
                    continue

                # 3. Stream Bulletin (Merge logic assumed or sequential play implementation)
                full_bulletin_url = story_videos[0] 
                s3_url = await workflow.execute_activity(upload_to_s3_activity, full_bulletin_url, start_to_close_timeout=timedelta(minutes=10))
                
                await workflow.execute_activity(
                    start_stream_activity,
                    {"channel_id": channel_id, "stream_key": stream_key, "video_url": s3_url, "is_promo": False},
                    start_to_close_timeout=timedelta(minutes=5)
                )

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
