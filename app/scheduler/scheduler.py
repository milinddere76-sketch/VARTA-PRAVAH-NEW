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
    if 5 <= hour < 10: return "सकाळ"
    elif 10 <= hour < 14: return "दुपार"
    elif 14 <= hour < 18: return "संध्याकाळ"
    elif 18 <= hour < 22: return "प्राइम टाइम"
    else: return "रात्री"

def main():
    print("🏢 [ENTERPRISE] VARTAPRAVAH TV Master Scheduler Active.")

    while True:
        try:
            # 0. Clean up old production artifacts
            cleanup_temp_files()
            
            bulletin_type = get_bulletin_type()
            print(f"🕒 [SCHEDULER] Slot: {bulletin_type}")
            
            articles = fetch_news()
            print(f"📰 [SCHEDULER] Found {len(articles)} articles from sources.")
            verified_articles = []

            for article in articles:
                title = article["title"] if isinstance(article, dict) else article
                if not is_verified(title):
                    print(f"❌ Skipping unverified news: {title[:50]}")
                    continue
                verified_articles.append(title)

            print(f"✅ [SCHEDULER] {len(verified_articles)} articles verified.")

            if verified_articles:
                # Process up to 5 verified articles individually per cycle (One Headline, One News rule)
                active_articles = verified_articles[:5]
                print(f"📰 [SCHEDULER] Processing {len(active_articles)} verified articles individually...")
                
                for index, article in enumerate(active_articles):
                    anchor_type = get_next_anchor()
                    prompt = f"BULLETIN_TYPE: {bulletin_type}\nANCHOR_TYPE: {anchor_type.upper()}\nRAW_HEADLINES:\n- {article}"
                    
                    # Generate a unique sequential task ID for each individual story
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
                        # Brief sleep to respect API rate limits during sequential generation
                        time.sleep(1)
            else:
                print("⏳ [SCHEDULER] No verified news available this cycle.")

            # 5-minute cycle for faster production
            time.sleep(300)

        except Exception as e:
            print(f"⚠️ [SCHEDULER] Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
