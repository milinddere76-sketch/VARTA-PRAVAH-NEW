import os
import uuid
import subprocess

def generate_ai_video(image, audio):
    """
    Sadtalker Service Wrapper.
    Executes synthesis inside the specialized GPU-enabled 'sadtalker' container.
    """
    # Unique output filename for tracking
    job_id = uuid.uuid4()
    output_file = f"/app/output/{job_id}.mp4"

    print(f"🎭 [SADTALKER-WRAPPER] Launching Remote CPU Synthesis Job: {job_id}")

    # Note: Using 'docker exec' to bridge the standard CPU node to the GPU synthesis node
    cmd = f"""
    docker exec sadtalker python3 /app/SadTalker/inference.py \
    --driven_audio {audio} \
    --source_image {image} \
    --result_dir /app/output \
    --size 512 \
    --enhancer gfpgan \
    --cpu \
    --still
    """

    # Execute the command via the Docker socket bridge
    import subprocess
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ [SADTALKER-ERROR] {result.stderr}")
        return None
    
    # Verify output file exists
    if os.path.exists(output_file):
        print(f"✅ [SADTALKER] Anchor video generated: {output_file}")
    else:
        print(f"⚠️ [SADTALKER] Output file not found at {output_file}")
    
    return output_file
