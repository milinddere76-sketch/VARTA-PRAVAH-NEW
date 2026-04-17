import os
import time
import subprocess

def generate_lipsync(audio_path, anchor):
    """
    Performs local lip-syncing using Wav2Lip inference.
    Required: Wav2Lip repository and pre-trained checkpoints.
    """
    # 1. Select the correct high-fidelity face portrait
    face = "/app/videos/female_anchor.jpg" if anchor == "female" else "/app/videos/male_anchor.jpg"

    # 2. Use unique output filename to support concurrent rendering and 24/7 stability
    ts = int(time.time())
    output = f"/app/videos/lipsync_{ts}.mp4"

    print(f"👄 [LIP-SYNC] Starting Wav2Lip for {anchor}...")

    # 3. Wav2Lip Inference Command
    cmd = [
        "python3", "Wav2Lip/inference.py",
        "--checkpoint_path", "Wav2Lip/checkpoints/wav2lip_gan.pth",
        "--face", face,
        "--audio", audio_path,
        "--outfile", output,
        "--pads", "0", "10", "0", "0" # Optional: adjust padding for better results
    ]

    try:
        # We use a 5-minute timeout as Wav2Lip can be slow on CPU
        subprocess.run(cmd, check=True, timeout=300)
        print(f"✅ Lip-sync complete: {output}")
        return output
    except Exception as e:
        print(f"❌ Lip-sync failed: {e}")
        # In case of failure, return the original face image (handled by activity renderer)
        return face 
