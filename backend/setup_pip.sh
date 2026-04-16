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
)

for pkg in "${packages[@]}"; do
    echo "📦 Installing $pkg..."
    pip install --no-cache-dir --prefer-binary \
        -i https://pypi.org/simple \
        --extra-index-url https://mirrors.pypi.io/simple \
        --default-timeout=1000 --retries 20 "$pkg"
done
