#!/bin/bash

# Define the absolute path to the news-ai folder based on current location
NEWS_AI_DIR=$(pwd)

echo "Installing Cron Job to run generating script every 3 hours..."

# Append the new cron job keeping existing ones intact
(crontab -l 2>/dev/null; echo "0 */3 * * * cd $NEWS_AI_DIR && /usr/bin/python3 script.py >> cron.log 2>&1") | crontab -

echo "✅ SUCCESS: Cron job installed!"
echo "Your AI news engine will automatically fetch headlines and render fresh broadcast videos every 3 hours."
