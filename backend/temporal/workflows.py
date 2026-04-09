from datetime import timedelta
from zoneinfo import ZoneInfo
from temporalio import workflow
from temporalio.common import RetryPolicy

from .activities import (
    fetch_news_activity,
    generate_script_activity,
    generate_audio_activity,
    generate_news_video_activity,
    upload_to_s3_activity,
    start_stream_activity,
    ensure_promo_video_activity,
    stop_stream_activity,
    check_scheduled_ads_activity,
    cleanup_old_videos_activity
)


# ================= STOP WORKFLOW ================= #

@workflow.defn
class StopStreamWorkflow:
    @workflow.run
    async def run(self, channel_id: int) -> str:
        return await workflow.execute_activity(
            stop_stream_activity,
            channel_id,
            start_to_close_timeout=timedelta(seconds=10)
        )


# ================= MAIN WORKFLOW ================= #

@workflow.defn
class NewsProductionWorkflow:
    @workflow.run
    async def run(self, input_data: dict) -> str:

        channel_id = input_data["channel_id"]
        language = input_data["language"]
        stream_key = input_data["stream_key"]

        ist = ZoneInfo("Asia/Kolkata")
        last_cleanup_day = -1
        is_female_anchor = False

        retry_policy = RetryPolicy(maximum_attempts=3)

        # ✅ Ensure promo exists
        await workflow.execute_activity(
            ensure_promo_video_activity,
            start_to_close_timeout=timedelta(seconds=120)
        )

        # ✅ Start with promo immediately
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

        # ================= LOOP ================= #

        while True:
            try:
                now = workflow.now().astimezone(ist)
                current_hour = now.strftime("%H")

                # ================= ADS ================= #
                ads = await workflow.execute_activity(
                    check_scheduled_ads_activity,
                    {"channel_id": channel_id, "hour": current_hour},
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy
                )

                for ad in ads:
                    await workflow.execute_activity(
                        start_stream_activity,
                        {
                            "channel_id": channel_id,
                            "stream_key": stream_key,
                            "video_url": ad,
                            "is_promo": False
                        },
                        start_to_close_timeout=timedelta(seconds=60)
                    )
                    await workflow.sleep(timedelta(seconds=35))

                # ================= NEWS ================= #

                is_female_anchor = not is_female_anchor

                news = await workflow.execute_activity(
                    fetch_news_activity,
                    language,
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy
                )

                script = await workflow.execute_activity(
                    generate_script_activity,
                    {"news_data": news, "language": language, "is_female": is_female_anchor},
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=retry_policy
                )

                audio = await workflow.execute_activity(
                    generate_audio_activity,
                    {"script": script.get("script", ""), "language": language},
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=retry_policy
                )

                video = await workflow.execute_activity(
                    generate_news_video_activity,
                    {
                        "title": news.get("headline", "Breaking News"),
                        "audio_url": audio
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=retry_policy
                )

                if not video:
                    await workflow.sleep(timedelta(minutes=5))
                    continue

                s3_url = await workflow.execute_activity(
                    upload_to_s3_activity,
                    video,
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=retry_policy
                )

                # ================= STREAM ================= #

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

                # ================= CLEANUP ================= #

                if now.day != last_cleanup_day:
                    await workflow.execute_activity(
                        cleanup_old_videos_activity,
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    last_cleanup_day = now.day

                # ================= SMART SLEEP ================= #

                if now.hour == 4 and now.minute >= 30:
                    five_am = now.replace(hour=5, minute=0, second=0, microsecond=0)
                    sleep_secs = (five_am - now).total_seconds()
                    await workflow.sleep(timedelta(seconds=max(sleep_secs, 0)))
                else:
                    await workflow.sleep(timedelta(minutes=30))

            except Exception:
                # ✅ FAILSAFE → always go to promo
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

                await workflow.sleep(timedelta(minutes=5))