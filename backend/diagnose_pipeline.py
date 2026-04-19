#!/usr/bin/env python3
"""
Comprehensive streaming pipeline diagnostic tool.
Run this to verify videos are being generated and queued correctly.
"""

import os
import requests
import subprocess
import time
from pathlib import Path

def check_videos_directory():
    """Check for generated news videos."""
    print("\n📁 Checking /app/videos directory...")
    video_dir = "/app/videos"
    
    if not os.path.exists(video_dir):
        print(f"  ❌ Directory not found: {video_dir}")
        return []
    
    files = sorted(
        [f for f in os.listdir(video_dir) if f.endswith('.mp4')],
        key=lambda f: os.path.getmtime(os.path.join(video_dir, f)),
        reverse=True
    )
    
    if not files:
        print(f"  ⚠️ No MP4 files found in {video_dir}")
        return []
    
    print(f"  ✅ Found {len(files)} video files:")
    for f in files[:5]:  # Show last 5
        fpath = os.path.join(video_dir, f)
        size_mb = os.path.getsize(fpath) / (1024*1024)
        mtime = time.ctime(os.path.getmtime(fpath))
        print(f"    - {f} ({size_mb:.1f}MB, {mtime})")
    
    return files

def check_broadcast_controller():
    """Check if broadcast controller is running and accessible."""
    print("\n🎬 Checking Broadcast Controller (port 8001)...")
    
    endpoints = [
        ("localhost", "http://localhost:8001"),
        ("127.0.0.1", "http://127.0.0.1:8001"),
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(f"{url}/status", timeout=2)
            if response.ok:
                data = response.json()
                print(f"  ✅ Reachable on {name}")
                print(f"    - Queue size: {data.get('queue_size', 'N/A')}")
                print(f"    - Streaming: {data.get('streaming', False)}")
                print(f"    - Current video: {data.get('current_video', 'None')}")
                print(f"    - Main process: {data.get('processes', {}).get('main', False)}")
                print(f"    - Pumper: {data.get('processes', {}).get('pumper', False)}")
                return True
            else:
                print(f"  ⚠️ HTTP {response.status_code} from {name}: {response.text}")
        except requests.exceptions.ConnectTimeout:
            print(f"  ⏱️ Timeout on {name}")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Cannot reach {name}")
        except Exception as e:
            print(f"  ❌ Error on {name}: {e}")
    
    return False

def test_add_video_endpoint(video_path):
    """Test the add-video endpoint."""
    print(f"\n🎥 Testing /add-video endpoint with: {os.path.basename(video_path)}")
    
    try:
        response = requests.post(
            "http://localhost:8001/add-video",
            json={"video": video_path},
            timeout=3
        )
        if response.ok:
            print(f"  ✅ Video queued successfully")
            print(f"    Response: {response.json()}")
            return True
        else:
            print(f"  ❌ Server returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def check_temporal_status():
    """Check if Temporal is running and workflows are executing."""
    print("\n⏱️ Checking Temporal Workflow Status...")
    
    try:
        # This would require the temporal CLI to be installed
        # For now, just check if workers are running
        result = subprocess.run(
            ["pgrep", "-f", "streaming_engine.worker"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            print(f"  ✅ Temporal worker process running (PID: {result.stdout.strip()})")
            return True
        else:
            print(f"  ❌ No Temporal worker process found")
            return False
    except Exception as e:
        print(f"  ⚠️ Could not check Temporal worker: {e}")
        return False

def check_backend_api():
    """Check if backend API is running."""
    print("\n🚀 Checking Backend API (port 8000)...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.ok:
            print(f"  ✅ Backend API running")
            return True
        else:
            print(f"  ⚠️ Backend API returned {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Cannot reach backend API: {e}")
        return False

def check_youtube_connectivity():
    """Check connectivity to YouTube RTMP server."""
    print("\n📡 Checking YouTube RTMP Connectivity...")
    
    try:
        import socket
        with socket.create_connection(("a.rtmp.youtube.com", 1935), timeout=3):
            print(f"  ✅ YouTube RTMP server reachable")
            return True
    except Exception as e:
        print(f"  ❌ Cannot reach YouTube: {e}")
        return False

def main():
    print("="*60)
    print("VARTA PRAVAH - STREAMING PIPELINE DIAGNOSTICS")
    print("="*60)
    
    # Run all checks
    videos = check_videos_directory()
    backend_ok = check_backend_api()
    controller_ok = check_broadcast_controller()
    temporal_ok = check_temporal_status()
    youtube_ok = check_youtube_connectivity()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Videos Generated: {'✅' if videos else '❌'} ({len(videos)} files)")
    print(f"  Backend API: {'✅' if backend_ok else '❌'}")
    print(f"  Broadcast Controller: {'✅' if controller_ok else '❌'}")
    print(f"  Temporal Worker: {'✅' if temporal_ok else '❌'}")
    print(f"  YouTube Connectivity: {'✅' if youtube_ok else '❌'}")
    
    # Recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if videos and not controller_ok:
        print("  ⚠️ Videos are being generated but broadcast controller is not reachable.")
        print("     - Check if broadcast_controller.py is running")
        print("     - Check if port 8001 is open")
        print("     - Try: python backend/broadcast_controller.py")
    
    if controller_ok and videos:
        print("  ✅ System appears to be working. Videos should be streaming!")
        if not youtube_ok:
            print("  ⚠️ But YouTube is not reachable. Stream key may be invalid.")
    
    if not videos:
        print("  ⚠️ No videos have been generated yet.")
        print("     - Check if Temporal workflows are running")
        print("     - Try triggering a news generation via API")
    
    if not backend_ok:
        print("  ❌ Backend API is not running. Start it first.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
