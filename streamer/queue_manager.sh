#!/bin/bash

# Varta Pravah - DYNAMIC QUEUE SYSTEM (The Brain)
# This script periodically scans for new news bulletins and updates the playout queue.

VIDEO_DIR="/home/ubuntu/videos"
PLAYLIST="/home/ubuntu/queue/playlist.txt"

echo "🧠 [QUEUE-MANAGER] Brain is active. Monitoring $VIDEO_DIR..."

while true; do
  # 1. Start fresh with the FFmpeg header
  echo "ffconcat version 1.0" > "$PLAYLIST"

  # 2. INTRO: Start with the Promo
  if [ -f "/app/assets/promo.mp4" ]; then
    echo "file '/app/assets/promo.mp4'" >> "$PLAYLIST"
  fi

  # 3. PRIORITY: Add Breaking News
  for file in "$VIDEO_DIR"/breaking/final_bulletin_*.mp4; do
    if [ -f "$file" ]; then
      echo "file '$file'" >> "$PLAYLIST"
    fi
  done

  # 4. STANDARD: Add regular news bulletins
  has_news=false
  for file in "$VIDEO_DIR"/final_bulletin_*.mp4; do
    if [ -f "$file" ]; then
      echo "file '$file'" >> "$PLAYLIST"
      has_news=true
      # Add a separator promo after every news item to keep branding high
      if [ -f "/app/assets/promo.mp4" ]; then
        echo "file '/app/assets/promo.mp4'" >> "$PLAYLIST"
      fi
    fi
  done

  # 5. IDLE: If no news, just loop the promo
  if [ "$has_news" = false ] && [ -f "/app/assets/promo.mp4" ]; then
      echo "file '/app/assets/promo.mp4'" >> "$PLAYLIST"
  fi

  # Wait 10 seconds before the next sync
  sleep 10
done
