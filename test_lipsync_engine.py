import os
import asyncio
import edge_tts
import requests
import time
from dotenv import load_dotenv

# --- CONFIG ---
MARATHI_TEXT = "नमस्कार, वार्ता प्रवाहमध्ये आपले स्वागत आहे. हे एक स्थानिक लिप-सिंक चाचणी आहे."
OUTPUT_AUDIO = "test_audio.mp3"
OUTPUT_VIDEO = "local_sync_test.mp4"

async def generate_audio(text):
    print("Generating Marathi audio...")
    voice = "mr-IN-AarohiNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(OUTPUT_AUDIO)
    print(f"Audio saved to {OUTPUT_AUDIO}")

def submit_to_synclabs(audio_url):
    print("Submitting to AI Lip-Sync Engine (Wav2Lip)...")
    load_dotenv()
    api_key = os.getenv("SYNCLABS_API_KEY")
    
    # Using official Sync.so demo assets to isolate the issue
    base_video = "https://assets.sync.so/docs/example-video.mp4"
    audio_url = "https://assets.sync.so/docs/example-audio.wav"
    
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "model": "lipsync-2",
        "input": [
            {"type": "video", "url": base_video},
            {"type": "audio", "url": audio_url}
        ]
    }
    
    r = requests.post("https://api.sync.so/v2/generate", headers=headers, json=payload)
    r.raise_for_status()
    job_id = r.json()["id"]
    print(f"Job submitted! ID: {job_id}")
    return job_id

def poll_and_download(job_id):
    print("Polling for result (this may take 45-60 seconds)...")
    api_key = os.getenv("SYNCLABS_API_KEY")
    headers = {"x-api-key": api_key}
    
    for i in range(20):
        r = requests.get(f"https://api.sync.so/v2/generate/{job_id}", headers=headers)
        data = r.json()
        status = data.get("status")
        print(f"   [{i+1}] Status: {status}")
        
        if status == "completed" or status == "COMPLETED":
            video_url = data["videoUrl"]
            print("Done! Downloading final video...")
            v_res = requests.get(video_url)
            with open(OUTPUT_VIDEO, "wb") as f:
                f.write(v_res.content)
            print(f"SUCCESS! Video saved as: {OUTPUT_VIDEO}")
            return
        elif status == "failed":
            print("Job failed.")
            return
        time.sleep(10)

async def main():
    # 1. Generate local audio
    await generate_audio(MARATHI_TEXT)
    
    # NOTE: To use SyncLabs, the audio MUST be accessible via URL.
    # In a local test, we usually upload to a temp service or use an existing URL.
    # For this test, I will use a high-quality pre-existing Marathi audio URL 
    # OR explain how to proceed.
    
    TEST_AUDIO_URL = "https://github.com/rany2/edge-tts/raw/master/tests/test_audio.mp3"
    
    print("\n--- TEST MODE ---")
    print("Using stable sample to test Lip-Sync Engine quality...")
    job_id = submit_to_synclabs(TEST_AUDIO_URL)
    poll_and_download(job_id)

if __name__ == "__main__":
    asyncio.run(main())
