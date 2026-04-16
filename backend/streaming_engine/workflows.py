from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio
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
    merge_videos_activity,
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
    def __init__(self):
        self._breaking_news_queue = []

    @workflow.signal
    def inject_breaking_news(self, news_data: dict):
        self._breaking_news_queue.append(news_data)

    @workflow.run
    async def run(self, channel_id: int, stream_key: str, language: str) -> None:
        last_bulletin_type = ""
        bulletin_index = 0
        ist = ZoneInfo("Asia/Kolkata")
        full_bulletin_path = "videos/promo.mp4"

        # 0. Initialize Premium Promo First (Essential for Zero-Gap)
        await workflow.execute_activity(
            ensure_premium_promo_activity, 
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # 0.1 IMMERSE BROADCAST (Instant YouTube Handshake)
        # We use a lower CPU priority for the first handshake to ensure it hits YouTube immediately
        await workflow.execute_activity(
            start_stream_activity, 
            {"channel_id": channel_id, "stream_key": stream_key, "video_url": "/app/videos/promo.mp4"}, 
            start_to_close_timeout=timedelta(minutes=1)
        )

        while True:
            try:
                # 0. CHECK BREAKING NEWS QUEUE (Immediate Priority)
                if self._breaking_news_queue:
                    news = self._breaking_news_queue.pop(0)
                    is_female = (bulletin_index % 2 == 0)
                    print(f"🔥 [BREAKING] Generating Flash for: {news['headline']}")
                    
                    b_s = await workflow.execute_activity(generate_script_activity, {"news_data": news, "is_female": is_female, "bulletin_type": "Breaking News"}, start_to_close_timeout=timedelta(minutes=3))
                    b_a = await workflow.execute_activity(generate_audio_activity, {"script": b_s["script"], "is_female": is_female}, start_to_close_timeout=timedelta(minutes=3))
                    
                    b_job = await workflow.execute_activity(synclabs_lip_sync_activity, {"audio_url": b_a, "is_female": is_female}, start_to_close_timeout=timedelta(minutes=3))
                    b_v = ""
                    if b_job not in ["no_api_key", "failed"]:
                        for _ in range(15):
                            b_poll = await workflow.execute_activity(check_sync_labs_status_activity, b_job, start_to_close_timeout=timedelta(minutes=1))
                            if b_poll["status"] == "completed":
                                b_v = b_poll["video_url"]
                                break
                            await workflow.sleep(timedelta(seconds=10))

                    if not b_v:
                        b_v = await workflow.execute_activity(generate_news_video_activity, {"title": "BREAKING NEWS", "audio_url": b_a, "is_female": is_female}, start_to_close_timeout=timedelta(minutes=3))
                    
                    await workflow.execute_activity(start_stream_activity, {"channel_id": channel_id, "stream_key": stream_key, "video_url": b_v}, start_to_close_timeout=timedelta(minutes=1))
                    await workflow.sleep(timedelta(minutes=1)) # Show for a bit

                # 1. SCHEDULED PRODUCTION CHECK
                current_time = datetime.now(ist).strftime("%H:%M")
                bulletin_type = "Standard Headlines"
                if "06:00" <= current_time < "11:00": bulletin_type = "Morning Bulletin"
                elif "11:00" <= current_time < "16:00": bulletin_type = "Afternoon Bulletin"
                elif "16:00" <= current_time < "19:30": bulletin_type = "Evening Bulletin"
                elif "19:30" <= current_time < "22:30": bulletin_type = "Prime Time"
                elif "22:30" <= current_time < "23:59" or "00:00" <= current_time < "05:00": bulletin_type = "Night Bulletin"

                if bulletin_type != last_bulletin_type:
                    print(f"🎬 [SCHEDULER] Producing {bulletin_type}")
                    is_female = (bulletin_index % 2 == 0)
                    bulletin_index += 1

                    news_items = await workflow.execute_activity(fetch_news_activity, language, start_to_close_timeout=timedelta(minutes=2))
                    items = (news_items if isinstance(news_items, list) else [news_items])[:25]

                    # Headlines (Sequential anchor intro)
                    h_res = await workflow.execute_activity(generate_headlines_activity, {"news_items": items, "is_female": is_female, "bulletin_type": bulletin_type}, start_to_close_timeout=timedelta(minutes=5))
                    h_a = await workflow.execute_activity(generate_audio_activity, {"script": h_res["script"], "is_female": is_female}, start_to_close_timeout=timedelta(minutes=5))
                    
                    h_job = await workflow.execute_activity(synclabs_lip_sync_activity, {"audio_url": h_a, "is_female": is_female}, start_to_close_timeout=timedelta(minutes=5))
                    h_v = ""
                    if h_job not in ["no_api_key", "failed"]:
                        for _ in range(20):
                            h_poll = await workflow.execute_activity(check_sync_labs_status_activity, h_job, start_to_close_timeout=timedelta(minutes=1))
                            if h_poll["status"] == "completed":
                                h_v = h_poll["video_url"]
                                break
                            await workflow.sleep(timedelta(seconds=10))

                    if not h_v:
                        h_v = await workflow.execute_activity(generate_news_video_activity, {"title": "HEADLINES", "audio_url": h_a, "is_female": is_female}, start_to_close_timeout=timedelta(minutes=5))

                    clips = [h_v] if h_v else []
                    
                    # Helper to produce a single story
                    async def produce_story(s):
                        try:
                            s_s = await workflow.execute_activity(generate_script_activity, {"news_data": s, "is_female": is_female, "bulletin_type": bulletin_type}, start_to_close_timeout=timedelta(minutes=5))
                            s_a = await workflow.execute_activity(generate_audio_activity, {"script": s_s["script"], "is_female": is_female}, start_to_close_timeout=timedelta(minutes=5))
                            s_job = await workflow.execute_activity(synclabs_lip_sync_activity, {"audio_url": s_a, "is_female": is_female}, start_to_close_timeout=timedelta(minutes=5))
                            
                            synced_v = ""
                            if s_job not in ["no_api_key", "failed"]:
                                for _ in range(30):
                                    poll = await workflow.execute_activity(check_sync_labs_status_activity, s_job, start_to_close_timeout=timedelta(minutes=2))
                                    if poll["status"] == "completed":
                                        synced_v = poll["video_url"]
                                        break
                                    await workflow.sleep(timedelta(seconds=10))

                            if synced_v:
                                return synced_v
                            
                            return await workflow.execute_activity(generate_news_video_activity, {"title": s.get("headline"), "audio_url": s_a, "is_female": is_female}, start_to_close_timeout=timedelta(minutes=5))
                        except Exception as e:
                            print(f"[WORKFLOW] Failed story item: {e}")
                            return None

                    # 2. Sequential/Batched Production of Story Clips (To prevent CPU saturation)
                    print(f"⚡ [SCHEDULER] Producing {len(items)} items in BATCHES of 5")
                    results = []
                    for i in range(0, len(items), 5):
                        batch = items[i:i+5]
                        batch_results = await asyncio.gather(*[produce_story(it) for it in batch])
                        results.extend(batch_results)
                        print(f"✅ [SCHEDULER] Batch complete: {len(results)}/{len(items)}")
                    
                    clips.extend([c for c in results if c])

                    # 3. Final Master Merge & Broadcast
                    final_v = await workflow.execute_activity(merge_videos_activity, {
                        "video_paths": clips,
                        "bulletin_type": bulletin_type,
                        "is_female": is_female
                    }, start_to_close_timeout=timedelta(minutes=10))
                    
                    await workflow.execute_activity(start_stream_activity, {
                        "channel_id": channel_id,
                        "stream_key": stream_key,
                        "video_url": final_v
                    }, start_to_close_timeout=timedelta(minutes=5))
                    
                    last_bulletin_type = bulletin_type

                print(f"📡 [AIR] Current Mode: {bulletin_type}. Standing by for Breaking News or Next Cycle...")
                
                # Wait for 15m OR until breaking news arrives
                await workflow.wait_condition(
                    lambda: len(self._breaking_news_queue) > 0,
                    timeout=timedelta(minutes=15)
                )

            except Exception as e:
                print(f"❌ [WORKFLOW CRITICAL ERROR] {e}")
                await workflow.sleep(timedelta(minutes=2))

@workflow.defn
class CheckBreakingNewsWorkflow:
    @workflow.run
    async def run(self) -> None:
        while True:
            try:
                # 1. Check for Breaking News
                from .activities import check_breaking_news_activity
                alerts = await workflow.execute_activity(
                    check_breaking_news_activity,
                    start_to_close_timeout=timedelta(minutes=2)
                )
                
                if alerts:
                    # Signal the production workflow
                    try:
                        handle = workflow.get_external_workflow_handle("news-production-auto")
                        for alert in alerts:
                            await handle.signal("inject_breaking_news", alert)
                            print(f"📡 [MONITOR] Breaking News Signaled: {alert.get('headline')}")
                    except: pass
                
                # 2. Wait 5 minutes
                await workflow.sleep(timedelta(minutes=5))
            except Exception as e:
                await workflow.sleep(timedelta(minutes=1))
