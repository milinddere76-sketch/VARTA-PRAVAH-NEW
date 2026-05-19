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

# SECURITY SHIELD: Handle SSH key permissions for Docker volumes
SAFE_KEY_PATH = "/tmp/oracle_key_safe.key"
def prepare_safe_key():
    if os.path.exists(config.ORACLE_KEY_PATH):
        try:
            print(f"🔐 [SECURITY] Hardening SSH key permissions...")
            # Copy to tmp to bypass read-only volume permission issues
            subprocess.run(["cp", config.ORACLE_KEY_PATH, SAFE_KEY_PATH], check=True)
            subprocess.run(["chmod", "600", SAFE_KEY_PATH], check=True)
            return SAFE_KEY_PATH
        except Exception as e:
            print(f"⚠️ [SECURITY] Failed to harden key: {e}")
    return config.ORACLE_KEY_PATH

# Initialize safe key
ACTIVE_KEY_PATH = prepare_safe_key()

def upload_to_oracle(video_path, is_breaking=False):
    """
    Python Upload Hook (STEP 4)
    Automated transfer of news bulletins to the Oracle relay node.
    """
    if not config.ORACLE_IP:
        print("⚠️ [PIPELINE] ORACLE_IP not set. Skipping upload.")
        return False

    filename = os.path.basename(video_path)
    
    # Priority handling: Breaking news goes to its own subfolder
    subfolder = "breaking/" if is_breaking else ""
    # Target specific filename for maximum reliability and ensure permissions
    remote_dest_tmp = f"{config.ORACLE_USER}@{config.ORACLE_IP}:{config.ORACLE_VIDEO_DIR}/{subfolder}{filename}.tmp"
    
    # HARDEN DESTINATION: Force permissions on remote folder before upload
    try:
        subprocess.run([
            "ssh", "-i", ACTIVE_KEY_PATH, "-o", "StrictHostKeyChecking=no",
            f"{config.ORACLE_USER}@{config.ORACLE_IP}",
            f"mkdir -p {config.ORACLE_VIDEO_DIR}/{subfolder} && sudo chmod 777 {config.ORACLE_VIDEO_DIR}/{subfolder}"
        ], timeout=15, capture_output=True)
    except:
        pass

    cmd = [
        "scp", "-i", ACTIVE_KEY_PATH,
        "-o", "StrictHostKeyChecking=no",
        video_path,
        remote_dest_tmp
    ]
    
    print(f"📤 [PIPELINE] Uploading {filename} to Oracle ({'BREAKING' if is_breaking else 'NORMAL'})...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            # ATOMIC RENAME: Convert .tmp to final .mp4 only after complete upload
            rename_cmd = [
                "ssh", "-i", ACTIVE_KEY_PATH,
                "-o", "StrictHostKeyChecking=no",
                f"{config.ORACLE_USER}@{config.ORACLE_IP}",
                f"mv {config.ORACLE_VIDEO_DIR}/{subfolder}{filename}.tmp {config.ORACLE_VIDEO_DIR}/{subfolder}{filename}"
            ]
            subprocess.run(rename_cmd, capture_output=True)
            print(f"✅ [PIPELINE] Upload Successful: {filename}")
            return True
        else:
            print(f"❌ [PIPELINE] Upload Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"🚨 [PIPELINE] Upload Error: {e}")
        return False

def add_to_queue(video_filename, is_breaking=False):
    """
    Incorporate news into the dynamic playout queue (STEP 5).
    """
    if not config.ORACLE_IP:
        return False

    subfolder = "breaking/" if is_breaking else ""
    remote_file_path = f"{config.ORACLE_VIDEO_DIR}/{subfolder}{video_filename}"
    
    remote_queue_path = f"{config.ORACLE_QUEUE_DIR}/playlist.txt"

    # Command to append the file to the oracle playlist queue
    cmd = [
        "ssh", "-i", ACTIVE_KEY_PATH,
        "-o", "StrictHostKeyChecking=no",
        f"{config.ORACLE_USER}@{config.ORACLE_IP}",
        f"mkdir -p {config.ORACLE_QUEUE_DIR} && sudo chmod 777 {config.ORACLE_QUEUE_DIR} && echo \"file '{remote_file_path}'\" >> {remote_queue_path}"
    ]
    
    print(f"🧠 [PIPELINE] Adding {video_filename} to Oracle Queue at {remote_queue_path}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️ [PIPELINE] Queue update failed: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"⚠️ [PIPELINE] Failed to update queue: {e}")
        return False

print("🎭 [SADTALKER-WORKER] Dedicated AI Face Engine starting...")
# init_tts() - Not needed in Light Mode

while True:
    # Listening for high-fidelity synthesis tasks
    data = r.blpop(config.QUEUE_NAME, timeout=5)

    if not data:
        time.sleep(1)
        continue

    try:
        task = json.loads(data[1])
        task_id = task["id"]
        script = task["script"]
        anchor_type = task.get("anchor_type", "female")
        
        print(f"🎙️ [SADTALKER-WORKER] Processing Task {task_id} for {anchor_type.upper()}...")

        # 1. News Style Formatting (Adds Anchor Feel)
        formatted_script = f"मुख्य बातम्या...\n\n{script}\n\nधन्यवाद।"
        
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
            final_path = video_engine.generate_video(sadtalker_video, script, final_video)
            
            if final_path and os.path.exists(final_path):
                # FIX 4: Proactively update the playlist for zero-downtime streaming
                from app.services.playlist_manager import generate_playlist
                generate_playlist()
                
                print(f"✅ [SADTALKER-WORKER] Bulletin Completed: {final_path}")
                
                # 5. AUTO-TRANSFER TO ORACLE (STEP 4)
                is_breaking = task.get("type") == "BREAKING"
                success = upload_to_oracle(final_path, is_breaking=is_breaking)
                
                if success:
                    # 6. INSTANT QUEUE INJECTION (STEP 5)
                    add_to_queue(final_video, is_breaking=is_breaking)

                    # 7. AUTO-CLEANUP (Hetzner)
                    print(f"🧹 [CLEANUP] Removing local file: {final_path}")
                    os.remove(final_path)
                    
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

        # LIMIT WORKER LOAD: Sleep for 60 seconds after each task to prevent CPU overload
        print(f"⏳ [LOAD-LIMIT] Cooldown for 60 seconds...")
        time.sleep(60)

    except Exception as e:
        print("🚨 [SADTALKER-WORKER] Critical Error:", e)
        r.incr("stats_errors_count")
        time.sleep(10)
