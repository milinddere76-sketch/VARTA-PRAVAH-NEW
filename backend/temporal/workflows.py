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
    stop_stream_activity,
    check_scheduled_ads_activity,
    cleanup_old_videos_activity
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
        channel_id = input_data["channel_id"]
        language = input_data["language"]
        stream_key = input_data["stream_key"]
        
        # 0. ENSURE ASSETS: Guarantee that the promo fallback exists
        await workflow.execute_activity(
            ensure_promo_video_activity,
            start_to_close_timeout=timedelta(seconds=120)
        )
        
        # 1. INITIAL BROADCAST: Go live with the promo loop IMMEDIATELY
        # This eliminates the "Black Screen" phase while the first news clip is generating.
        await workflow.execute_activity(
            start_stream_activity,
            {
                "channel_id": channel_id,
                "stream_key": stream_key,
                "video_url": "/app/videos/promo.mp4",
                "is_promo": True
            },
            start_to_close_timeout=timedelta(seconds=60)
        )
        last_cleanup_day = -1
        is_female_anchor = False
        ist = ZoneInfo("Asia/Kolkata")
        while True:
            try:
                # --- ADS & CUSTOM VIDEOS CHECK ---
                # Check for ads scheduled for this hour
                now = datetime.now(ist)
                current_hour_str = now.strftime("%H") # Just the hour "08", "12", etc.
                
                ad_segments = await workflow.execute_activity(
                    check_scheduled_ads_activity,
                    {"channel_id": channel_id, "hour": current_hour_str},
                    start_to_close_timeout=timedelta(seconds=60)
                )

                if ad_segments:
                    for ad_video_url in ad_segments:
                        print(f"Scheduled Ad Detected for {channel_id} @ {current_hour_str}. Injecting.")
                        await workflow.execute_activity(
                            start_stream_activity,
                            {
                                "channel_id": channel_id,
                                "stream_key": stream_key,
                                "video_url": ad_video_url,
                                "is_promo": False
                            },
                            start_to_close_timeout=timedelta(seconds=60)
                        )
                        # Give it a 30s min buffer for ads
                        await workflow.sleep(timedelta(seconds=35))
                
                # Toggle anchor for each loop iteration to add variety
                is_female_anchor = not is_female_anchor
                
                # 1. Fetch News
                news_data = await workflow.execute_activity(
                    fetch_news_activity,
                    language,
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )
                
                # 2. Script
                script_data = await workflow.execute_activity(
                    generate_script_activity,
                    {"news_data": news_data, "language": language, "is_female": is_female_anchor},
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )

                audio_path = await workflow.execute_activity(
                    generate_audio_activity,
                    {"script": script_data.get("script", ""), "language": language},
                    start_to_close_timeout=timedelta(minutes=120),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
                
                # 3. Generate News Video (Local - no SyncLabs dependency)
                final_video_url = await workflow.execute_activity(
                    generate_news_video_activity,
                    {
                        "title": news_data.get("headline", "Breaking News"),
                        "audio_url": audio_path,
                        "script": script_data.get("script", "")
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )

                # If the news generator returns an empty video URL, keep promo until next cycle.
                if not final_video_url:
                    print(f"News job completed without a valid video URL for channel {channel_id}. Keeping promo until next cycle.")
                    await workflow.sleep(timedelta(minutes=5))
                    continue

                # 5. Upload to S3
                s3_url = await workflow.execute_activity(
                    upload_to_s3_activity,
                    final_video_url,
                    start_to_close_timeout=timedelta(minutes=10)
                )
                
                # 6. Start / Update Stream (NEWS MODE)
                print(f"News Ready for Channel {channel_id}. Switching to News Stream.")
                await workflow.execute_activity(
                    start_stream_activity,
                    {
                        "channel_id": channel_id,
                        "stream_key": stream_key,
                        "video_url": s3_url,
                        "is_promo": False
                    },
                    start_to_close_timeout=timedelta(seconds=60)
                )
                
                # 7. Periodic Cleanup (Once per day)
                now = datetime.now(ist)
                if now.day != last_cleanup_day:
                    await workflow.execute_activity(
                        cleanup_old_videos_activity,
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    last_cleanup_day = now.day

                # 8. SMART SLEEPING: Calculate next run
                # If it's near midnight or morning, we can sleep until exactly 5 AM if desired,
                # but otherwise we do the 30-minute news rotation.
                
                # Check if we should wait for the specific 5 AM "Daily Generation"
                # If current time is between 4:30 AM and 5:00 AM, sleep exactly until 5:00.
                if now.hour == 4 and now.minute >= 30:
                    five_am = now.replace(hour=5, minute=0, second=0, microsecond=0)
                    sleep_secs = (five_am - now).total_seconds()
                    if sleep_secs > 0:
                        print(f"Approaching 5 AM refresh. Sleeping for {sleep_secs} seconds.")
                        await workflow.sleep(timedelta(seconds=sleep_secs))
                    else:
                        await workflow.sleep(timedelta(minutes=30))
                else:
                    # Normal rotation loop
                    await workflow.sleep(timedelta(minutes=30))

            except Exception as e:
                # 9. FAIL-SAFE: Play Promo Video
                print(f"Error in news generation (Channel {channel_id}): {e}. Playing Promo Fallback.")
                try:
                    await workflow.execute_activity(
                        start_stream_activity,
                        {
                            "channel_id": channel_id,
                            "stream_key": stream_key,
                            "video_url": "/app/videos/promo.mp4",
                            "is_promo": True
                        },
                        start_to_close_timeout=timedelta(seconds=60)
                    )
                except Exception as promo_e:
                    print(f"Fatal error: even the promo fallback failed: {promo_e}")
                
                # Wait 5 minutes and retry the news loop
                await workflow.sleep(timedelta(minutes=5))
