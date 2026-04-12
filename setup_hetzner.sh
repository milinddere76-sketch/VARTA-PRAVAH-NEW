#!/bin/bash

# VartaPravah Hetzner Server Setup Script
# Target: Ubuntu 22.04+

set -e

echo "🚀 Starting VartaPravah Server Setup..."

# 1. Update System
echo "🔄 Updating system packages..."
sudo apt update -y
sudo apt upgrade -y

# 2. Install Dependencies
echo "📦 Installing core dependencies..."
sudo apt install -y git curl ffmpeg python3-pip ca-certificates gnupg lsb-release

# 3. Install Docker (Official + Stable Way)
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker (Official Repo)..."

    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt update -y
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    sudo usermod -aG docker $USER
    echo "⚠️ Please log out and log back in for Docker permissions."
else
    echo "✅ Docker already installed."
fi

# 4. Install Docker Compose (Fix: modern systems use plugin)
if ! docker compose version &> /dev/null; then
    echo "🐙 Docker Compose plugin missing. Installing..."
    sudo apt install -y docker-compose-plugin
else
    echo "✅ Docker Compose already available."
fi

# 5. Application Setup
echo "📂 Preparing Application Directory..."

if [ ! -f "docker-compose.yml" ]; then
    echo "❌ ERROR: docker-compose.yml NOT found!"
    echo "👉 Run this script inside your project root folder."
    exit 1
else
    echo "✅ docker-compose.yml found."
fi

# 6. Environment Setup (Safe handling)
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        echo "📝 Creating .env from example..."
        cp backend/.env.example backend/.env
    else
        echo "⚠️ No .env.example found. Creating empty .env..."
        touch backend/.env
    fi

    echo "⚠️ IMPORTANT: Edit backend/.env before starting services."
fi

# 7. Start Services (Optional auto-start)
read -p "Do you want to start services now? (y/n): " choice
if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
    echo "🚀 Starting Docker services..."
    docker compose up -d --build
    echo "✅ Services started."
else
    echo "⏭️ Skipping service start."
fi

echo "===================================================="
echo "✅ VartaPravah Setup Complete!"
echo ""
echo "Next Steps:"
echo "1. Edit config: nano backend/.env"
echo "2. Start system: docker compose up -d --build"
echo ""
echo "Access:"
echo "Frontend: http://YOUR_SERVER_IP:3000"
echo "Backend:  http://YOUR_SERVER_IP:8000/docs"
echo "Temporal: http://YOUR_SERVER_IP:8088"
echo "===================================================="