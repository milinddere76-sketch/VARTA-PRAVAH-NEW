import redis
import json
import time
import os
import shutil
from datetime import datetime, timedelta
from app import config
from app.services.news_fetcher import fetch_news
from app.services.script_generator import generate_script
from app.services.fact_checker import is_verified

# Using config for flexibility
r = redis.Redis(host=config.REDIS_HOST, port=int(config.REDIS_PORT))

# --- 4-WAY ANCHOR ROTATION LOGIC ---
anchors = ["female1", "female2", "male1", "male2"]
anchor_index = 0

def get_next_anchor():
    global anchor_index
    selected = anchors[anchor_index]
    anchor_index = (anchor_index + 1) % len(anchors)
    return selected

def cleanup_temp_files():
    """
    Cleans up the output directory to prevent disk overflow.
    Removes files older than 6 hours.
    Equivalent to user's 'rm -rf /tmp/*' logic but for the project scope.
    """
    print("🧹 [CLEANUP] Purging old temp files from output directory...")
    now = time.time()
    for f in os.listdir(config.OUTPUT_DIR):
        file_path = os.path.join(config.OUTPUT_DIR, f)
        # Delete if older than 6 hours (21600 seconds)
        if os.stat(file_path).st_mtime < now - 21600:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"🗑️ Deleted: {f}")
            except Exception as e:
                print(f"⚠️ Failed to delete {f}: {e}")

def get_bulletin_type():
    hour = datetime.now().hour
    if 5 <= hour < 12: return "सुबह"        # Morning Slot
    elif 12 <= hour < 17: return "दोपहर"    # Afternoon Slot
    elif 17 <= hour < 21: return "प्राइम टाइम" # Evening Slot
    else: return "रात"                 # Night Slot

def main():
    print("🏢 [ENTERPRISE] VARTAPRAVAH TV Master Scheduler Active.")

    # 1. Run immediately on container startup to populate the playout queue
    print("🚀 [SCHEDULER] Initial startup run triggered. Populating active news queue...")
    try:
        cleanup_temp_files()
        bulletin_type = get_bulletin_type()
        articles = fetch_news()
        verified_articles = []
        for article in articles:
            if not is_verified(article):
                continue
            verified_articles.append(article)
            
        if verified_articles:
            active_articles = verified_articles[:6] # Enqueue up to 6 articles across categories
            for index, article in enumerate(active_articles):
                anchor_type = get_next_anchor()
                prompt = f"BULLETIN_TYPE: {bulletin_type}\nANCHOR_TYPE: {anchor_type.upper()}\nRAW_HEADLINES:\n- {article}"
                task_id = int(time.time()) * 1000 + index
                script = generate_script(prompt)
                if script:
                    r.rpush(config.QUEUE_NAME, json.dumps({
                        "id": task_id,
                        "type": bulletin_type,
                        "anchor_type": anchor_type,
                        "script": script
                    }))
                    print(f"✅ [{anchor_type.upper()}] Initial Story {index + 1} queued: {article[:50]}...")
                    time.sleep(1)
    except Exception as e:
        print(f"⚠️ [SCHEDULER-STARTUP] Error on initial run: {e}")

    last_triggered_time = None
    target_hours = [8, 14, 19, 23]

    while True:
        try:
            now = datetime.now()
            # Check if we match the top of the hour at minute 00 of our target hours
            if now.hour in target_hours and now.minute == 0:
                if last_triggered_time is None or last_triggered_time.hour != now.hour or last_triggered_time.date() != now.date():
                    last_triggered_time = now
                    
                    cleanup_temp_files()
                    bulletin_type = get_bulletin_type()
                    print(f"🕒 [SCHEDULER] Scheduled trigger at {now.strftime('%H:%M:%S')}. Slot: {bulletin_type}")
                    
                    articles = fetch_news()
                    print(f"📰 [SCHEDULER] Found {len(articles)} articles from sources.")
                    verified_articles = []

                    for article in articles:
                        if not is_verified(article):
                            print(f"❌ Skipping unverified news: {article[:50]}")
                            continue
                        verified_articles.append(article)

                    print(f"✅ [SCHEDULER] {len(verified_articles)} articles verified.")

                    if verified_articles:
                        # Clear old bulletins from Redis queue on new scheduled block to keep rotation fresh
                        print("🧹 [SCHEDULER] Clearing old queue items to rotate fresh slot bulletins...")
                        r.delete(config.QUEUE_NAME)
                        
                        active_articles = verified_articles[:6] # Process top 6 verified articles across categories
                        print(f"📰 [SCHEDULER] Processing {len(active_articles)} verified articles individually...")
                        
                        for index, article in enumerate(active_articles):
                            anchor_type = get_next_anchor()
                            prompt = f"BULLETIN_TYPE: {bulletin_type}\nANCHOR_TYPE: {anchor_type.upper()}\nRAW_HEADLINES:\n- {article}"
                            task_id = int(time.time()) * 1000 + index
                            
                            print(f"✍️ [ENTERPRISE] Generating individual script for Story {index + 1}/{len(active_articles)} ({anchor_type.upper()} anchor)...")
                            script = generate_script(prompt)

                            if script:
                                r.rpush(config.QUEUE_NAME, json.dumps({
                                    "id": task_id,
                                    "type": bulletin_type,
                                    "anchor_type": anchor_type,
                                    "script": script
                                }))
                                print(f"✅ [{anchor_type.upper()}] Story {index + 1} queued: {article[:50]}...")
                                time.sleep(1)
                    else:
                        print("⏳ [SCHEDULER] No verified news available for this scheduled slot.")
            
            # Check every 15 seconds
            time.sleep(15)

        except Exception as e:
            print(f"⚠️ [SCHEDULER] Error: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main()
