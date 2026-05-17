# VARTAPRAVAH - Production Deployment Guide

**Project:** Enterprise News Broadcasting System  
**Version:** 1.0  
**Date:** May 1, 2026  
**Status:** 🟢 READY FOR PRODUCTION

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Requirements](#system-requirements)
3. [Pre-Deployment Setup](#pre-deployment-setup)
4. [Hetzner Deployment](#hetzner-deployment)
5. [Oracle Cloud Deployment](#oracle-cloud-deployment)
6. [Post-Deployment Configuration](#post-deployment-configuration)
7. [Monitoring & Operations](#monitoring--operations)
8. [Troubleshooting Guide](#troubleshooting-guide)

---

## Architecture Overview

### System Design

```
                     ┌─────────────────┐
                     │   YouTube RTMP  │
                     │   rtmp://a.rtmp │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │  Oracle Cloud   │
                     │   Streamer      │
                     │  (1.9.3.1:1935) │◄──── RTMP Relay
                     └────────┬────────┘
                              │
                              │ (Network)
                              │
        ┌─────────────────────▼──────────────────────┐
        │              Hetzner Server                │
        │          (Primary Processing)              │
        ├─────────────────────────────────────────────┤
        │                                             │
        │  FastAPI (8000)                            │
        │  ├─ Dashboard                              │
        │  ├─ Analytics API                          │
        │  └─ Control Endpoints                      │
        │                                             │
        │  Services:                                 │
        │  ├─ TTS Engine (Marathi Audio)             │
        │  ├─ Video Generator (SadTalker)            │
        │  ├─ Script Processor                       │
        │  └─ News Fetcher                           │
        │                                             │
        │  Database Layer:                           │
        │  ├─ PostgreSQL (Persistent)                │
        │  ├─ Redis (Cache/Queue)                    │
        │  └─ File Storage (/output)                 │
        │                                             │
        │  Frontend (3000):                          │
        │  ├─ React Dashboard                        │
        │  ├─ Analytics View                         │
        │  └─ Control Panel                          │
        └─────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Role | Tech Stack |
|-----------|------|-----------|
| **Hetzner (Primary)** | AI Processing & Scheduling | Docker + Python + PostgreSQL |
| **Oracle Cloud (Secondary)** | RTMP Streaming Relay | Ubuntu + Nginx + FFmpeg + Liquidsoap |
| **Frontend** | Web Dashboard | React + Nginx |
| **Database** | Persistent Storage | PostgreSQL 15 |
| **Cache** | Real-time Metrics | Redis 7 |
| **Streaming** | Live Broadcasting | RTMP + HLS |

---

## System Requirements

### Hetzner Server Specifications

```
CPU: 8-core processor
RAM: 16 GB
Storage: 100 GB SSD (recommended)
Network: 1 Gbps dedicated
OS: Ubuntu 22.04 LTS or Debian 12
Docker: 20.10+
Docker Compose: 2.0+
```

### Oracle Cloud Server Specifications

```
CPU: 2-core ARM-based (Always Free Tier eligible)
RAM: 4 GB
Storage: 50 GB
Network: 1 Gbps
OS: Ubuntu 22.04 LTS (ARM64)
Docker: 20.10+
Docker Compose: 2.0+
```

### Local Development Requirements

```
Python: 3.10+
Node.js: 18+
npm: 9+
Docker Desktop: Latest
FFmpeg: 4.2+
Git: 2.30+
```

---

## Pre-Deployment Setup

### 1. Repository Preparation

```bash
# Clone the repository
git clone https://github.com/your-org/VARTAPRAVAH-LATEST.git
cd VARTAPRAVAH-LATEST

# Verify structure
ls -la
# Expected output shows:
# - Dockerfile.* files
# - docker-compose-*.yml files
# - app/ directory
# - frontend/ directory
# - .env file
```

### 2. Environment Configuration

Create `.env.production` file (Hetzner):

```bash
cat > .env.production << 'EOF'
# --- STREAM CONFIG ---
YOUTUBE_RTMP_URL=rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY

# --- DATABASE CONFIG ---
DATABASE_URL=postgresql://postgres:your_secure_password@postgres:5432/vartapravah
DB_HOST=postgres
DB_PORT=5432
DB_NAME=vartapravah
DB_USER=postgres
DB_PASS=your_secure_password

# --- REDIS CONFIG ---
REDIS_HOST=redis
REDIS_PORT=6379

# --- API KEYS ---
GROQ_API_KEY=your_groq_api_key
NEWS_API_KEY=your_newsapi_key
GOOGLE_TRANSLATE_API_KEY=your_google_api_key

# --- INFRASTRUCTURE ---
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1

# --- ORACLE RELAY ---
ORACLE_IP=161.118.173.23
ORACLE_USER=ubuntu
ORACLE_KEY_PATH=/app/oracle_key.key
ORACLE_VIDEO_DIR=/home/ubuntu/videos

# --- APPLICATION ---
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
USE_GPU=False
EOF

# Copy to .env
cp .env.production .env
```

### 3. SSH Key Setup

```bash
# For Oracle Cloud relay (if using private key authentication)
chmod 600 ssh-key-2026-04-23.key
```

### 4. Docker Registry Authentication (if using private registry)

```bash
docker login registry.your-domain.com
```

---

## Hetzner Deployment

### Step 1: Connect to Hetzner Server

```bash
ssh root@your-hetzner-ip

# Update system
apt-get update && apt-get upgrade -y

# Install curl and git
apt-get install -y curl git
```

### Step 2: Install Docker & Docker Compose

```bash
# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Step 3: Clone and Configure Repository

```bash
# Clone repository
git clone https://github.com/your-org/VARTAPRAVAH-LATEST.git
cd VARTAPRAVAH-LATEST

# Configure environment
nano .env  # Edit with your values

# Verify configuration
cat .env | grep -E "DATABASE_URL|YOUTUBE_RTMP|GROQ_API_KEY"
```

### Step 4: Build and Deploy Services

```bash
# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build images
docker-compose -f docker-compose-hetzner.yml build --no-cache

# Start services
docker-compose -f docker-compose-hetzner.yml up -d

# Verify services
docker-compose ps

# Expected output:
# CONTAINER ID   IMAGE                    STATUS
# xxxx           vartapravah_app          Up 2 seconds
# xxxx           vartapravah_worker       Up 1 second
# xxxx           vartapravah_frontend     Up 3 seconds
# xxxx           vartapravah_tts          Up 2 seconds
# xxxx           vartapravah_video        Up 1 second
# xxxx           postgres                 Up 3 seconds
# xxxx           redis                    Up 2 seconds
```

### Step 5: Initialize Database

```bash
# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready

# Create schema (if needed)
docker-compose exec app python -c "from database import init_db; init_db()"

# Verify database
docker-compose exec postgres psql -U postgres -d vartapravah -c "SELECT COUNT(*) FROM information_schema.tables;"
```

### Step 6: Health Verification

```bash
# Test API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy"}

# Test analytics endpoint
curl http://localhost:8000/api/analytics

# Test dashboard
curl -I http://localhost:8000/

# Test frontend
curl -I http://localhost:3000/
```

---

## Oracle Cloud Deployment

### Step 1: Connect to Oracle Cloud Server

```bash
ssh ubuntu@oracle-instance-ip

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 2: Configure Oracle Cloud Networking

```bash
# Open required ports in Oracle Cloud console:
# 1935 (RTMP)
# 8080 (HTTP)
# 8085 (HLS)

# Verify from local machine
nc -zv oracle-instance-ip 1935  # RTMP
nc -zv oracle-instance-ip 8085  # HLS
```

### Step 3: Deploy Streaming Service

```bash
# Clone repository
git clone https://github.com/your-org/VARTAPRAVAH-LATEST.git
cd VARTAPRAVAH-LATEST

# Configure environment
cp .env.production .env
nano .env  # Verify Oracle-specific settings

# Build and deploy
docker-compose -f docker-compose-oracle.yml build --no-cache
docker-compose -f docker-compose-oracle.yml up -d

# Verify
docker-compose ps
```

### Step 4: Configure RTMP Relay

```bash
# Edit nginx configuration if needed
docker-compose exec streamer bash -c "cat /etc/nginx/nginx.conf"

# Restart if configuration changes
docker-compose restart streamer

# Test RTMP availability
curl -I http://localhost:8080/stat
```

---

## Post-Deployment Configuration

### 1. Set Up SSL/TLS Certificates

```bash
# Install Certbot
apt-get install -y certbot python3-certbot-nginx

# Generate certificate for Hetzner frontend
certbot certonly --standalone -d your-domain.com

# Update nginx configuration to use SSL
# (Add SSL directives to nginx.conf in frontend container)
```

### 2. Configure Log Rotation

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/docker-vartapravah << 'EOF'
/var/lib/docker/containers/*/*-json.log {
  rotate 7
  daily
  compress
  delaycompress
  missingok
}
EOF
```

### 3. Set Up Automated Backups

```bash
# Create backup script
cat > /home/ubuntu/backup-db.sh << 'EOF'
#!/bin/bash
cd /path/to/VARTAPRAVAH-LATEST
docker-compose exec postgres pg_dump -U postgres vartapravah | gzip > backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz
# Keep only last 7 days of backups
find backups -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /home/ubuntu/backup-db.sh

# Schedule daily backup
echo "0 2 * * * /home/ubuntu/backup-db.sh" | crontab -
```

### 4. Configure Monitoring & Alerts

```bash
# Install htop for system monitoring
apt-get install -y htop

# Monitor container resource usage
docker stats

# Set up log monitoring
docker-compose logs -f app
```

---

## Monitoring & Operations

### Daily Operations

```bash
# Check service status
docker-compose ps

# View logs (last 50 lines)
docker-compose logs --tail=50

# Monitor real-time
docker stats

# Check disk usage
df -h

# Check database size
docker-compose exec postgres psql -U postgres -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database ORDER BY pg_database_size(pg_database.datname) DESC;"
```

### Performance Metrics

```bash
# Redis memory usage
docker-compose exec redis redis-cli info memory

# PostgreSQL connections
docker-compose exec postgres psql -U postgres -c "SELECT count(*) as connections FROM pg_stat_activity;"

# API response time
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
```

### Alerting Setup

Set up monitoring for:
- Container restarts
- High memory usage (>80%)
- High disk usage (>85%)
- Database connection failures
- API response time > 1s

---

## Troubleshooting Guide

### Issue: Container Won't Start

```bash
# Check logs
docker-compose logs app

# Verify environment variables
docker-compose config

# Restart service
docker-compose restart app

# Rebuild if needed
docker-compose build --no-cache app
```

### Issue: Database Connection Failed

```bash
# Test connection
docker-compose exec app psql $DATABASE_URL -c "SELECT 1"

# Check PostgreSQL logs
docker-compose logs postgres

# Verify database exists
docker-compose exec postgres psql -U postgres -l
```

### Issue: High Memory Usage

```bash
# Check which container uses memory
docker stats

# Restart problematic service
docker-compose restart app

# Check for memory leaks
docker-compose logs app | grep -i "memory\|error"
```

### Issue: No Streaming to YouTube

```bash
# Verify RTMP URL is correct
grep YOUTUBE_RTMP .env

# Test RTMP connection from Oracle
docker-compose exec streamer bash -c "echo 'RTMP_ADDR' && netstat -tulpn | grep 1935"

# Check streamer logs
docker-compose logs streamer

# Test push to YouTube manually
ffmpeg -f lavfi -i testsrc=duration=10:size=1280x720:rate=30 -f lavfi -i sine=frequency=1000:duration=10 -pix_fmt yuv420p -c:v libx264 -c:a aac -f flv rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
```

### Issue: Disk Space Low

```bash
# Check disk usage
du -sh ./output/*

# Clean old videos
find ./output -type f -name "*.mp4" -mtime +30 -delete

# Clean docker system
docker system prune -a

# Check docker storage
docker system df
```

---

## Rollback Procedure

If something goes wrong:

```bash
# 1. Stop all services
docker-compose down

# 2. Check git status
git status

# 3. Revert to last known good commit
git log --oneline
git revert <commit-hash>

# 4. Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# 5. Verify
docker-compose logs -f app
```

---

## Success Checklist

Before considering deployment complete, verify:

- [ ] All containers are running and healthy
- [ ] Database is accessible and initialized
- [ ] Frontend loads on port 3000
- [ ] API responds on port 8000
- [ ] Health endpoint returns 200 OK
- [ ] Analytics data being recorded
- [ ] YouTube RTMP streaming working
- [ ] Logs show no critical errors
- [ ] Backups are scheduled
- [ ] Monitoring is active

---

## Support & Documentation

- **Main Dashboard:** http://hetzner-ip:3000
- **API Docs:** http://hetzner-ip:8000/docs
- **Logs:** `docker-compose logs -f`
- **Backup Location:** `/home/ubuntu/backups/`
- **Config:** `.env` file in project root

---

**Deployment Complete! 🎉**

*Last Updated: May 1, 2026*
