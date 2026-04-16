#!/bin/bash
set -e
packages=(
    "fastapi>=0.115.0"
    "uvicorn[standard]>=0.30.0"
    "pydantic>=2.10.0"
    "sqlalchemy>=2.0.49"
    "psycopg>=3.3.3"
    "temporalio>=1.26.0"
    "groq>=0.11.2"
    "edge-tts>=7.2.8"
    "pillow>=12.2.0"
    "requests>=2.32.0"
    "httpx>=0.27.0"
    "python-dotenv>=1.0.1"
    "python-multipart"
)

# 🚀 OFFLINE INSTALLATION (AIR-GAPPED)
echo "📦 Installing from local wheels folder..."
if [ -d "./wheels" ] && [ "$(ls -A ./wheels)" ]; then
    pip install --no-index --find-links=./wheels "${packages[@]}"
    echo "✅ Offline installation successful!"
    exit 0
else
    echo "⚠️ Local wheels not found. Falling back to internet (might fail on this server)..."
    pip install "${packages[@]}"
fi
