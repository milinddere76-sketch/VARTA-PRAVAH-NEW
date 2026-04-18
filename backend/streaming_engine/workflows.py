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

                    # 🚨 TRIGGER FULL-SCREEN BUMPER
                    if is_breaking_news(news["headline"]):
                        print("🚨 [WORKFLOW] High-Priority News Detected! Playing Bumper...")
                        await workflow.execute_activity(
                            "play_breaking",
                            start_to_close_timeout=timedelta(minutes=1)
                        )
                        # Let the bumper play for 10 seconds before the news starts
                        await workflow.sleep(timedelta(seconds=10))

                    anchor = await workflow.execute_activity(
                        "get_anchor",
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                    is_female = (anchor == "female")
                    anchor_label = "FEMALE (Priya)" if is_female else "MALE (Arjun)"
                    print(f"🔥 [BREAKING] Generating Flash with {anchor_label} anchor for: {news['headline']}")
                    bulletin_index += 1 
                    
                    b_s = await workflow.execute_activity(
                        generate_script_activity, 
                        (news, "Breaking News", True, anchor), 
                        start_to_close_timeout=timedelta(minutes=3)
                    )
                    b_a = await workflow.execute_activity(
                        generate_audio_activity, 
                        (b_s["script"], anchor), 
                        start_to_close_timeout=timedelta(minutes=3)
                    )
                    
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
                        b_v = await workflow.execute_activity(
                            generate_news_video_activity, 
                            (b_a, "BREAKING NEWS", anchor, True), 
                            start_to_close_timeout=timedelta(minutes=3)
                        )
                    
                    await workflow.execute_activity(start_stream_activity, {"channel_id": channel_id, "stream_key": stream_key, "video_url": b_v}, start_to_close_timeout=timedelta(minutes=1))
                    await workflow.sleep(timedelta(minutes=1)) # Show for a bit

                # 1. SCHEDULED PRODUCTION CHECK
                # 1. MASTER SCHEDULE COMPLIANCE
                target_slots = ["05:00", "12:00", "17:00", "20:00", "23:00"]
                now = datetime.now(ist)
                current_time_str = now.strftime("%H:%M")
                
                active_slot = None
                for slot in target_slots:
                    slot_dt = datetime.strptime(slot, "%H:%M").replace(
                        year=now.year, month=now.month, day=now.day, tzinfo=ist
                    )
                    # Prepare 15 mins before
                    prep_window_start = slot_dt - timedelta(minutes=15)
                    
                    if prep_window_start <= now < slot_dt:
                        active_slot = slot
                        break
                
                # Check if we need to produce for the upcoming/current slot
                if active_slot and active_slot != last_bulletin_type:
                    bulletin_type = f"{active_slot} Bulletin"
                    
                    # Persistent Toggle via Manager Activity
                    anchor = await workflow.execute_activity(
                        "get_anchor",
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                    is_female = (anchor == "female")
                    anchor_label = "FEMALE (Priya)" if is_female else "MALE (Arjun)"
                    print(f"🎬 [MASTER SCHEDULE] 15-Min Prep started for {bulletin_type} with {anchor_label}")
                    bulletin_index += 1

                    news_items = await workflow.execute_activity(fetch_news_activity, language, start_to_close_timeout=timedelta(minutes=2))
                    items = (news_items if isinstance(news_items, list) else [news_items])[:15] # 15 items for stability

                    # Sequential Production (To ensure stability on resource-constrained server)
                    results = []
                    for it in items:
                        try:
                            res = await self.produce_story(it, bulletin_type, anchor, is_female)
                            if res:
                                results.append(res)
                                print(f"✅ [SCHEDULER] Item complete: {len(results)}/{len(items)}")
                        except Exception as e:
                            print(f"⚠️ [SCHEDULER] Item failed: {e}")
                    
                    # 3. Final Master Merge & Broadcast
                    final_v = await workflow.execute_activity(merge_videos_activity, {
                        "video_paths": results,
                        "bulletin_type": bulletin_type,
                        "is_female": is_female
                    }, start_to_close_timeout=timedelta(minutes=10))
                    
                    # WAIT UNTIL EXACT SLOT TIME TO GO LIVE
                    now_check = datetime.now(ist)
                    target_dt = datetime.strptime(active_slot, "%H:%M").replace(
                        year=now_check.year, month=now_check.month, day=now_check.day, tzinfo=ist
                    )
                    if now_check < target_dt:
                        wait_seconds = (target_dt - now_check).total_seconds()
                        print(f"⌛ [MASTER SCHEDULE] Render complete. Waiting {wait_seconds}s for air-time...")
                        await workflow.sleep(timedelta(seconds=wait_seconds))

                    await workflow.execute_activity(start_stream_activity, {
                        "channel_id": channel_id,
                        "stream_key": stream_key,
                        "video_url": final_v
                    }, start_to_close_timeout=timedelta(minutes=5))
                    
                    last_bulletin_type = active_slot

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
