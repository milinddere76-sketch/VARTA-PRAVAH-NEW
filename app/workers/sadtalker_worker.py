import redis
import json
import time
import os
import subprocess
from app import config
from app.services.tts_engine import generate_audio
from app.services.video_engine import VideoEngine

# Dedicated SadTalker Worker Configuration
r = redis.Redis(host=config.REDIS_HOST, port=int(config.REDIS_PORT))
video_engine = VideoEngine()

os.makedirs(config.OUTPUT_DIR, exist_ok=True)



print("🎭 [SADTALKER-WORKER] Dedicated AI Face Engine starting...")
# init_tts() - Not needed in Light Mode

while True:
    # Listening for high-fidelity synthesis tasks
    try:
        data = r.blpop(config.QUEUE_NAME, timeout=5)
    except (redis.exceptions.TimeoutError, redis.exceptions.ConnectionError):
        time.sleep(1)
        continue

    if not data:
        time.sleep(1)
        continue

    try:
        task = json.loads(data[1])
        task_id = task["id"]
        raw_script = task["script"]
        anchor_type = task.get("anchor_type", "female")
        
        print(f"🎙️ [SADTALKER-WORKER] Processing Task {task_id} for {anchor_type.upper()}...")

        # Parse TICKER and SCRIPT components
        ticker_text = ""
        anchor_script = ""
        
        if "TICKER:" in raw_script and "SCRIPT:" in raw_script:
            try:
                parts = raw_script.split("SCRIPT:")
                ticker_text = parts[0].replace("TICKER:", "").strip()
                anchor_script = parts[1].strip()
            except Exception as parse_err:
                print(f"⚠️ [SADTALKER-WORKER] Parse error: {parse_err}")
                ticker_text = ""
                anchor_script = raw_script
        else:
            anchor_script = raw_script
            
        if not ticker_text:
            # Clean fallback: remove greetings for ticker if parsing failed
            ticker_text = anchor_script
            for greeting in ["नमस्कार, वार्ता प्रवाह में आपका स्वागत है।", "नमस्कार, वार्ता प्रवाह मध्ये आपले स्वागत आहे."]:
                ticker_text = ticker_text.replace(greeting, "")
            for signoff in ["इस खबर पर अधिक जानकारी और अन्य अपडेट के लिए देखते रहिए, वार्ता प्रवाह। धन्यवाद!", "याबाबत पुढील तपशील आणि इतर घडामोडींसाठी पाहत राहा, वार्ता प्रवाह. धन्यवाद!"]:
                ticker_text = ticker_text.replace(signoff, "")
            ticker_text = ticker_text.strip()
            
        # 1. News Style Formatting (Adds Anchor Feel)
        formatted_script = f"मुख्य समाचार...\n\n{anchor_script}\n\nधन्यवाद।"
        
        # 2. Neural TTS Synthesis
        audio_file = os.path.join(config.OUTPUT_DIR, f"audio_{task_id}.mp3")
        generate_audio(formatted_script, audio_file, anchor_type=anchor_type)

        if not os.path.exists(audio_file):
            print("❌ [SADTALKER-WORKER] TTS Failed")
            continue

        # 2. LEAN SYNTHESIS: Generate a video loop from anchor image + audio
        face_image = None
        for ext in [".png", ".jpg", ".jpeg"]:
            test_path = os.path.join(config.ASSETS_DIR, f"anchor_{anchor_type}{ext}")
            if os.path.exists(test_path):
                face_image = test_path
                break
        
        if not face_image:
            print(f"❌ [SADTALKER-WORKER] Missing face image for anchor {anchor_type}")
            continue
            
        sadtalker_video = os.path.join(config.OUTPUT_DIR, f"lean_bulletin_{task_id}.mp4")
        tmp_sadtalker_video = sadtalker_video + ".tmp"
        
        print(f"⚡ [LEAN-MODE] Generating high-speed loop using OPTIMIZED command with {os.path.basename(face_image)}...")
        # Upgraded to ARM64-Robust command
        lean_cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", face_image,
            "-i", audio_file,
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-r", "25", "-s", "1280x720", "-shortest",
            "-f", "mp4",
            tmp_sadtalker_video
        ]
        
        result = subprocess.run(lean_cmd, capture_output=True, text=True)
        print(f"📊 [FFMPEG-DEBUG] Command: {' '.join(lean_cmd)}")
        print(f"📊 [FFMPEG-DEBUG] Return Code: {result.returncode}")
        
        if result.returncode == 0 and os.path.exists(tmp_sadtalker_video):
            os.rename(tmp_sadtalker_video, sadtalker_video)
        else:
            if os.path.exists(tmp_sadtalker_video):
                os.remove(tmp_sadtalker_video)
                
        print(f"📊 [FFMPEG-DEBUG] target_video: {sadtalker_video}")
        print(f"📊 [FFMPEG-DEBUG] exists in python: {os.path.exists(sadtalker_video)}")
        if result.returncode != 0:
            print(f"❌ [FFMPEG-ERROR] Stderr: {result.stderr}")
            print(f"❌ [FFMPEG-ERROR] Stdout: {result.stdout}")
        
        if os.path.exists(sadtalker_video):
            # 4. Final Video Composition (Ticker + Overlays)
            final_video = f"final_bulletin_{task_id}.mp4"
            final_path = video_engine.generate_video(sadtalker_video, ticker_text, final_video)
            
            if final_path and os.path.exists(final_path):
                # FIX 4: Proactively update the playlist for zero-downtime streaming
                from app.services.playlist_manager import generate_playlist
                generate_playlist()
                
                print(f"✅ [SADTALKER-WORKER] Bulletin Completed: {final_path}")
                
                # In single-server mode, the video remains locally in config.OUTPUT_DIR
                # for the streamer to play from the shared volume
                is_breaking = task.get("type") == "BREAKING"
                if is_breaking:
                    # For breaking news, copy to breaking subfolder
                    import shutil
                    filename = os.path.basename(final_path)
                    dest_dir = os.path.join(config.OUTPUT_DIR, "breaking")
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, filename)
                    try:
                        shutil.copy2(final_path, dest_path)
                        print(f"✅ [LOCAL-SINGLE-SERVER] Copied Breaking News to: {dest_path}")
                        # Remove original standard bulletin to avoid duplicate playout
                        if os.path.exists(final_path):
                            os.remove(final_path)
                    except Exception as e:
                        print(f"⚠️ [LOCAL-SINGLE-SERVER] Failed to copy breaking news: {e}")
                else:
                    print(f"✅ [LOCAL-SINGLE-SERVER] Standard bulletin ready at: {final_path}")
                    
                r.rpush("ready_videos", final_path)
                r.incr("stats_videos_generated")
            else:
                print("❌ [SADTALKER-WORKER] Composition Failed")
                r.incr("stats_errors_count")
        else:
            print("❌ [SADTALKER-WORKER] SadTalker Synthesis Failed")
            r.incr("stats_errors_count")
        # STORAGE MANAGEMENT: Auto-delete files older than 1 day
        print(f"🧹 [STORAGE] Cleaning up old bulletins...")
        os.system("find /app/output -type f -mtime +1 -delete")
        try:
            from app.services.playlist_manager import generate_playlist
            generate_playlist()
        except Exception as pe:
            print(f"⚠️ [SADTALKER-WORKER] Playlist rebuild failed: {pe}")

        # LIMIT WORKER LOAD: Sleep for 60 seconds after each task to prevent CPU overload
        print(f"⏳ [LOAD-LIMIT] Cooldown for 60 seconds...")
        time.sleep(60)

    except Exception as e:
        print("🚨 [SADTALKER-WORKER] Critical Error:", e)
        r.incr("stats_errors_count")
        time.sleep(10)
