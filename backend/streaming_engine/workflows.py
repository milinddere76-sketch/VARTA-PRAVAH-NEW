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
        bulletin_index = 0   # increments each loop → alternates anchor

        # ── 0. Ensure promo fallback asset exists ─────────────────────────
        await workflow.execute_activity(
            ensure_promo_video_activity,
            start_to_close_timeout=timedelta(seconds=300)  # 3-attempt generation needs time
        )

        # ── 1. Go LIVE immediately with promo while first news clip generates ─
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
        ist = ZoneInfo("Asia/Kolkata")

        while True:
            try:
                # ── Switch to PROMO at the start of every cycle ───────────
                # This ensures viewers see the channel promo during the
                # 5-15 minutes it takes to fetch/generate/render news,
                # instead of a stale old bulletin looping indefinitely.
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

                anchor_slot  = bulletin_index % 2          # 0 = female, 1 = male
                is_female    = (anchor_slot == 0)
                bulletin_index += 1

                # ── Ads check ─────────────────────────────────────────────
                now = datetime.now(ist)
                current_hour_str = now.strftime("%H")

                ad_segments = await workflow.execute_activity(
                    check_scheduled_ads_activity,
                    {"channel_id": channel_id, "hour": current_hour_str},
                    start_to_close_timeout=timedelta(seconds=60)
                )

                if ad_segments:
                    for ad_video_url in ad_segments:
                        print(f"Injecting scheduled ad for channel {channel_id} @ hour {current_hour_str}")
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
                        await workflow.sleep(timedelta(seconds=35))

                # ── 0. Ensure Assets ──────────────────────────────────────
                await workflow.execute_activity(ensure_promo_video_activity, channel_id, start_to_close_timeout=timedelta(minutes=5))
                await workflow.execute_activity(ensure_premium_promo_activity, start_to_close_timeout=timedelta(minutes=5))

                # ── 1. Fetch news ─────────────────────────────────────────
                news_data = await workflow.execute_activity(
                    fetch_news_activity,
                    language,
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )

                # ── 2. Generate script (gender-aware) ────────────────────
                script_data = await workflow.execute_activity(
                    generate_script_activity,
                    {"news_data": news_data, "language": language, "is_female": is_female},
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )

                # ── 3. TTS audio ──────────────────────────────────────────
                audio_path = await workflow.execute_activity(
                    generate_audio_activity,
                    {"script": script_data.get("script", ""), "language": language},
                    start_to_close_timeout=timedelta(minutes=120),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )

                # ── 4. Render news video ──────────────────────────────────
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

                if not final_video_url:
                    print(f"No video URL for channel {channel_id}. Keeping promo.")
                    await workflow.sleep(timedelta(minutes=5))
                    continue

                # ── 5. Upload / resolve URL ───────────────────────────────
                s3_url = await workflow.execute_activity(
                    upload_to_s3_activity,
                    final_video_url,
                    start_to_close_timeout=timedelta(minutes=10)
                )

                # ── 6. Switch stream to news video ────────────────────────
                anchor_label = "Priya Desai (Female)" if is_female else "Arjun Sharma (Male)"
                print(f"📺 Bulletin #{bulletin_index} | Anchor: {anchor_label} | Channel: {channel_id}")
                import os
                news_video_path = final_video_url.split("?")[0] # strip any query params
                
                # SANITY CHECK: Minimum size for a 720p news video with audio should be > 500KB
                # 161KB or smaller usually indicates a corrupted/empty video header
                if os.path.exists(news_video_path) and os.path.getsize(news_video_path) > 500 * 1024:
                    await workflow.execute_activity(
                        start_stream_activity,
                        {
                            "channel_id": channel_id,
                            "stream_key": stream_key,
                            "video_url": s3_url,
                            "is_promo": False
                        },
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    # Keep news on for 5 mins (or length of video)
                    await workflow.sleep(timedelta(minutes=5))
                    
                    # ── 7. Post-Bulletin Promo (1 Minute) ──────────────
                    print(f"🎬 Transitioning to Premium Promo for 1 min...")
                    await workflow.execute_activity(
                        start_stream_activity,
                        {
                            "channel_id": channel_id,
                            "stream_key": stream_key,
                            "video_url": "/app/videos/premium_promo.mp4",
                            "is_promo": True
                        },
                        start_to_close_timeout=timedelta(minutes=2)
                    )
                    await workflow.sleep(timedelta(minutes=1))
                else:
                    workflow.logger.error(f"Generated news video {s3_url} is too small or missing. Staying on promo.")
                    # If news failed, we don't fall back here because the promo is ALREADY running from Step 1.
                    # We just wait for the next cycle.
                    await workflow.sleep(timedelta(minutes=2))

                # ── 7. Daily cleanup ──────────────────────────────────────
                now = datetime.now(ist)
                if now.day != last_cleanup_day:
                    await workflow.execute_activity(
                        cleanup_old_videos_activity,
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    last_cleanup_day = now.day

                # ── 8. Smart sleep (30 min normal, align to 5 AM) ─────────
                if now.hour == 4 and now.minute >= 30:
                    five_am = now.replace(hour=5, minute=0, second=0, microsecond=0)
                    sleep_secs = (five_am - now).total_seconds()
                    if sleep_secs > 0:
                        await workflow.sleep(timedelta(seconds=sleep_secs))
                    else:
                        await workflow.sleep(timedelta(minutes=30))
                else:
                    await workflow.sleep(timedelta(minutes=30))

            except Exception as e:
                print(f"⚠️ News generation error (channel {channel_id}): {e}. Falling back to promo.")
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
                    print(f"❌ Promo fallback also failed: {promo_e}")

                await workflow.sleep(timedelta(minutes=5))
