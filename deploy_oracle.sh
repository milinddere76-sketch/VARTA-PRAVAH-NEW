#!/bin/bash

echo "======================================"
echo "☁️ VARTAPRAVAH ORACLE CLOUD ZERO-PC DEPLOYMENT ☁️"
echo "======================================"

echo "[1/4] Updating Package Lists..."
sudo apt update

echo "[2/4] Installing Core Server Dependencies..."
sudo apt install python3 python3-pip python3-venv ffmpeg git -y

echo "[3/4] Creating Virtual Environment..."
python3 -m venv venv
source venv/bin/activate

echo "[3/4] Installing Python AI Libraries..."
pip install requests groq gtts python-dotenv

# Note: Keeping openai here just in case user needs legacy plugins, though Groq is primary
pip install openai 

echo "======================================"
echo "✅ SUCCESS: Oracle Cloud Environment Ready!"
echo "======================================"
echo "To begin your broadcast:"
echo "1. Nano into backend/.env and paste your API keys"
echo "2. Run: python backend/batch_generate.py"
echo "3. Run: nohup python backend/streamer.py > stream.log 2>&1 &"
echo "======================================"
