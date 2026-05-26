#!/bin/bash

# Configuration
VIDEO_DIR="/app/videos"
LOCAL_FALLBACK="/app/assets/promo.mp4"
# Build target list for FFmpeg tee muxer

TEE_TARGETS="[f=flv:onfail=ignore]rtmp://127.0.0.1:1935/live/stream"
if [ -n "$YOUTUBE_RTMP_URL" ]; then
    TEE_TARGETS="${TEE_TARGETS}|[f=flv:onfail=ignore]${YOUTUBE_RTMP_URL}"
fi
if [ -n "$FACEBOOK_RTMP_URL" ]; then
    TEE_TARGETS="${TEE_TARGETS}|[f=flv:onfail=ignore]${FACEBOOK_RTMP_URL}"
fi

echo "🚀 [STREAMER] Starting Varta Pravah Broadcast..."

while true
do
  # Clean up: Remove videos older than 60 minutes to save disk space
  find "$VIDEO_DIR" -type f -name "*.mp4" -mmin +60 -delete 2>/dev/null
  
  # Find all mp4 files in the video directory
  VIDEOS=($(ls $VIDEO_DIR/*.mp4 2>/dev/null))
  
  if [ ${#VIDEOS[@]} -gt 0 ]; then
    for SOURCE in "${VIDEOS[@]}"
    do
      echo "🌐 [PRIMARY] Broadcasting: $(basename "$SOURCE")"
      
      ffmpeg -re -i "$SOURCE" \
        -c:v libx264 -preset veryfast -maxrate 3000k -bufsize 6000k \
        -pix_fmt yuv420p -g 50 \
        -c:a aac -b:a 128k \
        -f tee "$TEE_TARGETS"
        
      echo "✅ Finished streaming $(basename "$SOURCE")"
      sleep 2
    done
  else
    echo "🛡️ [FALLBACK] No news bulletins found in $VIDEO_DIR. Streaming promo..."
    
    ffmpeg -re -i "$LOCAL_FALLBACK" \
      -c:v libx264 -preset veryfast -maxrate 3000k -bufsize 6000k \
      -pix_fmt yuv420p -g 50 \
      -c:a aac -b:a 128k \
      -f tee "$TEE_TARGETS"
      
    echo "⚠️ Fallback loop ended. Checking for new news in 10s..."
    sleep 10
  fi
done
