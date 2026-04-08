#!/bin/bash

# VartaPravah Hetzner Server Setup Script
# Target: Ubuntu 22.04+

set -e

echo "🚀 Starting VartaPravah Server Setup..."

# 1. Update System
echo "🔄 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install Dependencies
echo "📦 Installing core dependencies (ffmpeg, git, curl)..."
sudo apt install -y git curl ffmpeg python3-pip

# 3. Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "✅ Docker already installed."
fi

# 4. Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "🐙 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker Compose already installed."
fi

# 5. Application Setup
echo "📂 Preparing Application Directory..."
# Note: This assumes the script is run inside the cloned repository
# If not, we could add git clone logic here if we know the repo URL.

if [ -f "docker-compose.yml" ]; then
    echo "✅ docker-compose.yml found."
else
    echo "⚠️ docker-compose.yml NOT found in current directory!"
    echo "Please run this script from the root of the VartaPravah repository."
fi

# 6. Environment Setup
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating .env from example..."
    cp backend/.env.example backend/.env
    echo "⚠️ IMPORTANT: Please edit backend/.env with your API keys before running 'docker-compose up -d'."
fi

echo "===================================================="
echo "✅ Setup Complete!"
echo "Next Steps:"
echo "1. Run: nano backend/.env (Fill in your keys)"
echo "2. Run: docker-compose up -d --build"
echo "===================================================="
