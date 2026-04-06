#!/bin/bash

# Configuration
# Source .env file if it exists to get any local environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi
YOUTUBE_KEY="${YOUTUBE_STREAM_KEY:-qcu7-xesd-m4sv-9zvv-e335}"
PLAYLIST_FILE="playlist.txt"
VIDEOS_DIR="videos"

echo "📡 Starting Vartapravah 24x7 Auto-Loop Streamer..."

# 1. Build the playlist.txt automatically from the videos directory
echo "📁 Generating $PLAYLIST_FILE..."
rm -f $PLAYLIST_FILE
for f in $VIDEOS_DIR/bulletin_*.mp4; do
    if [ -e "$f" ] && [[ "$f" != *"PROMO"* ]]; then
        echo "file '$f'" >> $PLAYLIST_FILE
        # Inject Promo filler after each standard bulletin
        if [ -e "$VIDEOS_DIR/bulletin_PROMO.mp4" ]; then
            echo "file '$VIDEOS_DIR/bulletin_PROMO.mp4'" >> $PLAYLIST_FILE
        fi
    fi
done

# Check if playlist is empty
if [ ! -s $PLAYLIST_FILE ]; then
    echo "⚠️ Error: No videos found in $VIDEOS_DIR/ ! Please run script.py first to generate the bulletins."
    exit 1
fi

echo "✅ Playlist active:"
cat $PLAYLIST_FILE

echo "🔴 Commencing Continuous RTMP Stream to YouTube..."
# 2. Run the continuous FFmpeg Auto-Loop. Wrapped in while-true to automatically reconnect!
while true; do
    echo "Starting FFmpeg stream..."
    ffmpeg -re -stream_loop -1 -fflags +genpts -f concat -safe 0 -i $PLAYLIST_FILE -c copy -f flv rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_KEY
    echo "⚠️ Stream disconnected or crashed. Soft restarting in 5 seconds to maintain uptime..."
    sleep 5
done
