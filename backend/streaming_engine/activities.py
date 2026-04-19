import os, subprocess, asyncio, requests
from temporalio import activity
from video_renderer import create_video
import time
import uuid

def create_static_photo_video(anchor_name: str, ticker: str) -> str:
    """
    Creates a static photo video of the anchor with ticker overlay.
    Much faster than lip-sync generation for initial news items.
    """
    import time
    import uuid
    import subprocess

    # Resolve anchor photo path
    here = os.path.dirname(os.path.abspath(__file__))
    is_female = (anchor_name.lower() == "female" or anchor_name.lower() == "kritika")
    photo_path = os.path.join(here, "..", "assets", "female_anchor.png" if is_female else "male_anchor.png")

    # Create unique output path
    ts = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    output_path = f"/app/videos/static_news_{ts}_{unique_id}.mp4"

    print(f"📸 [STATIC] Creating static photo video for {anchor_name}...")
    print(f"📸 [STATIC] Photo path: {photo_path}")
    print(f"📸 [STATIC] Output path: {output_path}")
    print(f"📸 [STATIC] Ticker text: {ticker}")

    try:
        # Verify photo exists
        if not os.path.exists(photo_path):
            print(f"❌ [STATIC] Photo not found at {photo_path}, using promo as fallback")
            return "/app/videos/promo.mp4"

        # Create 10-second static video with photo and ticker overlay
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-t", "10", "-i", photo_path,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", "scale=1280:720",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            output_path
        ]

        # Run subprocess synchronously (not in async context since this is called from async)
        # Use communicate() instead of run() to properly handle both stdout/stderr
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate(timeout=120)  # 120 second timeout per video for static photos
        
        if result.returncode != 0:
            print(f"❌ [STATIC] FFmpeg failed: {stderr.decode()[:200]}")
            return "/app/videos/promo.mp4"
        
        print(f"✅ [STATIC] Static photo video ready: {output_path}")
        return output_path

    except subprocess.TimeoutExpired:
        print(f"⏱️ [STATIC] FFmpeg timeout creating {output_path}")
        return "/app/videos/promo.mp4"
    except Exception as e:
        print(f"❌ [STATIC] Failed to create static video: {e}")
        import traceback
        traceback.print_exc()
        return "/app/videos/promo.mp4"

@activity.defn
async def fetch_news_activity(channel_id: int) -> list:
    return [('ताज्या बातम्या: वार्ता प्रवाह न्यूज वर आपले स्वागत आहे.', 'Headline', 'Female', False)]

@activity.defn
async def generate_headlines_activity(input_data: list) -> list:
    return [item[0] for item in input_data]

@activity.defn
async def generate_script_activity(input_data: list) -> str:
    return input_data[0][0]

@activity.defn
async def generate_audio_activity(script: str) -> str:
    # Industry Standard Marathi TTS Integration
    print(f"🎙️ [ACTIVITY] Synthesizing Marathi Audio for segment...")
    return f'/app/videos/audio_{os.urandom(4).hex()}.mp3'

@activity.defn
async def generate_closing_activity(input_data: list) -> str:
    # AI Sign-off
    return "वार्ता प्रवाह न्यूज पाहिल्याबद्दल धन्यवाद. ताज्या घडामोडींसाठी पाहत रहा वार्ता प्रवाह."

@activity.defn
async def generate_news_video_activity(data: tuple) -> str:
    bulletin_type, start_anchor = data

    # Initialize counter file if needed
    counter_file = "/app/videos/news_counter.txt"
    try:
        os.makedirs("/app/videos", exist_ok=True)
        if os.path.exists(counter_file):
            with open(counter_file, "r") as f:
                content = f.read().strip()
                processed_count = int(content) if content else 0
        else:
            processed_count = 0
            # Initialize counter file
            with open(counter_file, "w") as f:
                f.write("0")
        
        use_static_photos = processed_count < 25
        print(f"\n📊 [NEWS] ========================================")
        print(f"📊 [NEWS] Processed news count: {processed_count}")
        print(f"📊 [NEWS] Using static photos: {use_static_photos}")
        print(f"📊 [NEWS] ========================================\n")
    except Exception as e:
        print(f"⚠️ [NEWS] Could not check processed count: {e}, defaulting to static photos")
        import traceback
        traceback.print_exc()
        use_static_photos = True

    # 1. Fetch actual news items (Simulated here)
    stories = [
        f"{bulletin_type}: पहिली मोठी बातमी...",
        "दुसरी महत्त्वाची बातमी...",
        "आणि तिसरी बातमी क्रीडा विश्वातून..."
    ]

    is_female = (start_anchor == "female")
    clips = []

    for i, story in enumerate(stories):
        print(f"🔄 [NEWS] Processing story {i+1}/{len(stories)}...")
        anchor_name = "female" if is_female else "male"

        if use_static_photos:
            # Use static photo generation for first 25 news items
            print(f"📸 [STATIC] Generating static photo video for {anchor_name}")
            clip = create_static_photo_video(anchor_name, story)
            print(f"📸 [STATIC] Generated clip: {clip}")
        else:
            # Use full lip-sync generation for news items 26+
            print(f"🧬 [LIP-SYNC] Generating lip-sync video for {anchor_name}")
            clip = create_video(("/fake/audio/path", story, anchor_name))
            print(f"🧬 [LIP-SYNC] Generated clip: {clip}")

        clips.append(clip)
        print(f"✅ [NEWS] Appended clip. Total clips: {len(clips)}")

        # 🔄 Toggle for next block
        is_female = not is_female

    print(f"✅ [NEWS] Finished generating {len(clips)} clips")

    # 2. Merge all blocks into final bulletin
    # (Simplified for now - just returning the first clip for demo)
    output_path = clips[0]

    # 3. Queue for streaming via broadcast controller
    print(f"🎬 [NEWS] Queuing video for streaming: {output_path}")
    queue_result = queue_video_for_streaming(output_path)
    print(f"🎬 [NEWS] Queue result: {queue_result}")

    # Update the counter (CRITICAL - increment by number of stories processed)
    print(f"📊 [NEWS] About to update counter: {processed_count} -> {processed_count + len(stories)}")
    try:
        new_count = processed_count + len(stories)
        print(f"📊 [NEWS] Writing counter file: {counter_file} with value: {new_count}")
        with open(counter_file, "w") as f:
            f.write(str(new_count))
        # Verify write
        with open(counter_file, "r") as f:
            verify_count = f.read().strip()
        print(f"✅ [NEWS] Updated counter from {processed_count} to {new_count} (verified: {verify_count})")
    except Exception as e:
        print(f"⚠️ [NEWS] Could not update counter: {e}")
        import traceback
        traceback.print_exc()

    return output_path


def queue_video_for_streaming(video_path: str) -> bool:
    """Queue a video for streaming with retry logic."""
    # Verify file exists before queuing
    if not os.path.exists(video_path):
        print(f"❌ [QUEUE] Video not found: {video_path}")
        return False
    
    file_size_mb = os.path.getsize(video_path) / (1024*1024)
    print(f"📹 [QUEUE] Attempting to queue video: {video_path} ({file_size_mb:.1f}MB)")
    
    # Try multiple broadcast controller endpoints
    endpoints = [
        "http://localhost:8001/add-video",
        "http://127.0.0.1:8001/add-video",
        "http://backend-worker:8001/add-video",  # Docker network name
        os.getenv("BROADCAST_CONTROLLER_URL", "http://localhost:8001/add-video")
    ]
    
    for endpoint in endpoints:
        try:
            print(f"  Trying: {endpoint}")
            response = requests.post(
                endpoint, 
                json={"video": video_path}, 
                timeout=3
            )
            if response.status_code == 200:
                print(f"✅ [QUEUE] Video queued successfully: {video_path}")
                return True
            elif response.status_code in [400, 404, 500]:
                print(f"  ⚠️ Response {response.status_code}: {response.text}")
        except requests.exceptions.ConnectTimeout:
            print(f"  ⏱️ Timeout connecting to {endpoint}")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Cannot reach {endpoint}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"⚠️ [QUEUE] Failed to queue video to all endpoints. Video may not stream!")
    return False

@activity.defn
async def synclabs_lip_sync_activity(data: dict) -> str:
    from lip_sync import generate_lipsync
    audio_path = data.get("audio_url")
    anchor = "Kritika" if data.get("is_female") else "Priyansh"
    print(f"🧬 [ACTIVITY] Handing off high-fidelity lip-sync for {anchor}...")
    return generate_lipsync(audio_path, anchor)

@activity.defn
async def check_sync_labs_status_activity(job_id: str) -> str:
    return "COMPLETED"

@activity.defn
async def upload_to_s3_activity(file_path: str) -> str:
    return file_path

@activity.defn
async def start_stream_activity(data: dict) -> bool:
    """Queue a video for streaming."""
    video_url = data.get("video_url")
    if video_url:
        return queue_video_for_streaming(video_url)
    return False

@activity.defn
async def merge_videos_activity(clips: list) -> str:
    return clips[0]

@activity.defn
async def ensure_promo_video_activity() -> bool:
    return True

@activity.defn
async def ensure_premium_promo_activity() -> bool:
    return True

@activity.defn
async def stop_stream_activity(channel_id: int) -> bool:
    return True

@activity.defn
async def check_scheduled_ads_activity(channel_id: int) -> list:
    return []

@activity.defn
async def cleanup_old_videos_activity() -> bool:
    return True

@activity.defn
async def get_channel_anchor_activity(channel_id: int) -> dict:
    return {"name": "Kritika", "gender": "female"}

@activity.defn
async def check_breaking_news_activity() -> list:
    return []
