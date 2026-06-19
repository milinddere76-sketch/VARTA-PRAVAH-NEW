#!/bin/bash

# Varta Pravah - NO STOP STREAM (PRO Architecture)
# This script uses the FFmpeg concat demuxer to play a dynamic playlist.

PLAYLIST="/home/ubuntu/queue/playlist.txt"
LOG_FILE="/home/ubuntu/logs/playout.log"

echo "🚀 [PRO-PLAYOUT] Starting continuous broadcast engine..."

# Wait for the Brain to create the first playlist
WAIT_COUNT=0
while [ ! -f "$PLAYLIST" ]; do
  echo "⏳ [WAIT] Waiting for Queue Manager to generate the first playlist..."
  sleep 2
  WAIT_COUNT=$((WAIT_COUNT + 1))
  if [ $WAIT_COUNT -gt 15 ]; then
    echo "⚠️ [WARN] Queue Manager taking too long! Forcing initial playlist generation..."
    mkdir -p $(dirname "$PLAYLIST")
    echo "ffconcat version 1.0" > "$PLAYLIST"
    if [ -f "/app/assets/promo.mp4" ]; then
        echo "file '/app/assets/promo.mp4'" >> "$PLAYLIST"
    else
        # Extreme fallback
        ffmpeg -f lavfi -i color=c=black:s=1280x720:d=5 -f lavfi -i aevalsrc=0:d=5 -c:v libx264 -c:a aac -y /app/assets/fallback_standby.mp4
        echo "file '/app/assets/fallback_standby.mp4'" >> "$PLAYLIST"
    fi
    break
  fi
done

# Build target list for FFmpeg tee muxer
TEE_TARGETS="[f=flv:onfail=ignore]rtmp://127.0.0.1:1935/live/stream"
if [ -n "$YOUTUBE_RTMP_URL" ]; then
    TEE_TARGETS="${TEE_TARGETS}|[f=flv:onfail=ignore]${YOUTUBE_RTMP_URL}"
fi

# Bitrate Configuration
BITRATE="${STREAM_BITRATE:-2500k}"
BUFSIZE="${STREAM_BUFSIZE:-5000k}"

while true; do

  # Use environment variable if present, otherwise default to the provided key
  echo "📺 [PLAYOUT] Starting live broadcast at $BITRATE..."
  ffmpeg -re -f concat -safe 0 -i "$PLAYLIST" \
    -f lavfi -i anoisesrc=c=white:a=0.001:r=44100 \
    -filter_complex "[0:v]scale=1280:720,format=yuv420p,fps=25[v]; [0:a]aformat=channel_layouts=stereo[a0]; [a0][1:a]amix=inputs=2:duration=first[amixout]; [amixout]volume=2[a]" \
    -map "[v]" -map "[a]" \
    -c:v libx264 -preset ultrafast -tune zerolatency -b:v "$BITRATE" -minrate "$BITRATE" -maxrate "$BITRATE" -bufsize "$BUFSIZE" \
    -threads 0 -g 50 -keyint_min 50 -x264-params "keyint=50:nal-hrd=cbr" \
    -vsync cfr \
    -r 25 \
    -c:a aac -b:a 128k -ar 44100 -shortest -f tee \
    "$TEE_TARGETS"


  echo "⚠️ [$(date)] Stream ended or crashed. Restarting in 2s..." >> "$LOG_FILE"
  sleep 2
done

