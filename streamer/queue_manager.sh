#!/bin/bash

# Varta Pravah - DYNAMIC QUEUE SYSTEM (The Brain)
# This script periodically scans for new news bulletins and updates the playout queue.

VIDEO_DIR="/home/ubuntu/videos"
PLAYLIST="/home/ubuntu/queue/playlist.txt"
TMP_PLAYLIST="/tmp/playlist.txt.tmp"

echo "🧠 [QUEUE-MANAGER] Brain is active. Monitoring $VIDEO_DIR..."

# Create playlist directory if it doesn't exist
mkdir -p "$(dirname "$PLAYLIST")"

while true; do
  # STRICT PLayout Age Limit: Automatically purge any news video file older than 3 days
  find "$VIDEO_DIR" -type f -name "final_bulletin_*.mp4" -mtime +3 -delete
  find "$VIDEO_DIR" -type f -name "lean_bulletin_*.mp4" -mtime +3 -delete

  # Dynamic Ad-Slot Injection: 3-minute window every 15 minutes
  CURRENT_MINUTES=$(( $(date +%s) / 60 ))
  MOD_MINUTES=$(( CURRENT_MINUTES % 15 ))
  PROMO_FILE="/app/assets/promo.mp4"
  if [ $MOD_MINUTES -lt 3 ]; then
    ADS=($(ls /home/ubuntu/videos/ads/*.mp4 2>/dev/null | sort))
    if [ ${#ADS[@]} -gt 0 ]; then
      SLOT_INDEX=$(( CURRENT_MINUTES / 15 ))
      AD_INDEX=$(( SLOT_INDEX % ${#ADS[@]} ))
      PROMO_FILE="${ADS[$AD_INDEX]}"
    elif [ -f "/app/assets/priyansh_creations_adv.mp4" ]; then
      PROMO_FILE="/app/assets/priyansh_creations_adv.mp4"
    fi
  fi


  # 1. Start fresh in a temp file
  echo "ffconcat version 1.0" > "$TMP_PLAYLIST"

  # 2. PRIORITY: Add Breaking News
  for file in "$VIDEO_DIR"/breaking/final_bulletin_*.mp4; do
    if [ -f "$file" ]; then
      if ! ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$file" >/dev/null 2>&1; then
        if [ $(( $(date +%s) - $(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null || echo 0) )) -gt 60 ]; then
          echo "⚠️ [QUEUE-MANAGER] Breaking file $file is corrupt. Removing..."
          rm -f "$file"
        else
          echo "⏳ [QUEUE-MANAGER] Breaking file $file is currently writing. Skipping..."
        fi
        continue
      fi
      echo "file '$file'" >> "$TMP_PLAYLIST"
    fi
  done

  # 4. STANDARD: Add regular news bulletins (Limit to latest 10, newest first)
  has_news=false
  for file in $(ls -t "$VIDEO_DIR"/final_bulletin_*.mp4 2>/dev/null | head -n 10); do
    if [ -f "$file" ]; then
      if ! ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$file" >/dev/null 2>&1; then
        if [ $(( $(date +%s) - $(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null || echo 0) )) -gt 60 ]; then
          echo "⚠️ [QUEUE-MANAGER] File $file is corrupt or incomplete. Removing..."
          rm -f "$file"
        else
          echo "⏳ [QUEUE-MANAGER] File $file is currently writing. Skipping..."
        fi
        continue
      fi
      echo "file '$file'" >> "$TMP_PLAYLIST"
      has_news=true
      # Add a separator promo/ad after every news item to keep branding high
      if [ -f "$PROMO_FILE" ]; then
        echo "file '$PROMO_FILE'" >> "$TMP_PLAYLIST"
      fi
    fi
  done

  # 4b. FALLBACK: If no final bulletins, include lean bulletins from local output
  if [ "$has_news" = false ]; then
    echo "⚠️ [QUEUE-MANAGER] No final bulletins found. Falling back to lean bulletins..."
    for file in $(ls -t "$VIDEO_DIR"/lean_bulletin_*.mp4 2>/dev/null | head -n 10); do
      if [ -f "$file" ]; then
        if ! ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$file" >/dev/null 2>&1; then
          if [ $(( $(date +%s) - $(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null || echo 0) )) -gt 60 ]; then
            echo "⚠️ [QUEUE-MANAGER] File $file is corrupt or incomplete. Removing..."
            rm -f "$file"
          else
            echo "⏳ [QUEUE-MANAGER] File $file is currently writing. Skipping..."
          fi
          continue
        fi
        echo "📰 [QUEUE-MANAGER] Adding lean bulletin: $file"
        echo "file '$file'" >> "$TMP_PLAYLIST"
        has_news=true
        if [ -f "$PROMO_FILE" ]; then
          echo "file '$PROMO_FILE'" >> "$TMP_PLAYLIST"
        fi
      fi
    done
  fi

  # 5. IDLE: If no news, just loop the promo/ad
  if [ "$has_news" = false ] && [ -f "$PROMO_FILE" ]; then
      echo "file '$PROMO_FILE'" >> "$TMP_PLAYLIST"
  fi

  # 6. COMPARE AND HOT-RELOAD
  if [ ! -f "$PLAYLIST" ]; then
    # Initial playlist creation
    mv "$TMP_PLAYLIST" "$PLAYLIST"
    echo "🆕 [QUEUE-MANAGER] Initialized new playout queue."
  elif ! cmp -s "$TMP_PLAYLIST" "$PLAYLIST"; then
    # Playlist has changed! Update and restart FFmpeg for hot reload.
    mv "$TMP_PLAYLIST" "$PLAYLIST"
    echo "🔄 [QUEUE-MANAGER] Playlist updated! Hot-reloading FFmpeg..."
    pkill -f "ffmpeg.*concat" || true
  else
    # No changes, clean up temp file
    rm -f "$TMP_PLAYLIST"
  fi

  # Wait 10 seconds before the next sync
  sleep 10
done
