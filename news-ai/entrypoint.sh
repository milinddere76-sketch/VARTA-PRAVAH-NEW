#!/bin/bash
set -e

echo "================================================="
echo "☁️ STARTING VARTAPRAVAH CLOUD ZERO-PC CONTAINER ☁️"
echo "================================================="

# Pre-compile the first set of videos immediately so the stream doesn't fail
python script.py

# Launch the stream logic in the background
nohup bash stream.sh > stream_logs.txt 2>&1 &

# Endless Generation Loop (Docker Cron Equivalent)
while true; do
  echo "Sleeping for 3 hours to conserve Free Tier limits..."
  sleep 10800
  
  echo "Waking up to generate fresh bulletins..."
  python script.py
done
