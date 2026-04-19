# VartaPravah Production Deployment Guide

## Overview
This guide covers deploying VartaPravah to production with the latest streaming pipeline fixes.

## Prerequisites
- Docker and Docker Compose installed
- Git repository access
- YouTube stream key configured
- Domain/server with public IP

## Environment Variables
Create a `.env` file in the project root:

```bash
# Required API Keys
GROQ_API_KEY=your_groq_api_key_here
WORLD_NEWS_API_KEY=your_world_news_api_key_here
SYNCLABS_API_KEY=your_synclabs_api_key_here

# YouTube Streaming
YOUTUBE_STREAM_KEY=your_youtube_stream_key_here

# Optional: Custom ports (defaults shown)
BACKEND_PORT=8000
BROADCAST_CONTROLLER_PORT=8001
TEMPORAL_PORT=7233
TEMPORAL_UI_PORT=8080
```

## Quick Production Deploy

### 1. Clone and Setup
```bash
git clone https://github.com/milinddere76-sketch/VARTA-PRAVAH-NEW.git
cd VARTA-PRAVAH-NEW
cp .env.example .env  # Edit with your keys
```

### 2. Build and Deploy
```bash
# Build all services
docker compose build

# Start production stack
docker compose up -d

# Wait for services to initialize (2-3 minutes)
sleep 180

# Check deployment status
curl http://localhost:8000/debug/pipeline
```

### 3. Verify Streaming Pipeline
```bash
# Check all services are running
docker ps

# Run comprehensive diagnostics
python backend/diagnose_pipeline.py

# Check broadcast controller status
curl http://localhost:8001/status
```

## Service Architecture

### Core Services
- **postgres**: Database for news articles and channel config
- **temporal**: Workflow orchestration engine
- **temporal-ui**: Web interface for workflow monitoring
- **backend**: FastAPI server with news generation endpoints
- **backend-worker**: Temporal worker for async video processing
- **frontend**: Next.js web interface (optional)

### Streaming Pipeline
1. **Temporal Workflows** generate news videos every 15 minutes
2. **Activities** create video content and queue for streaming
3. **Broadcast Controller** manages video queue and YouTube streaming
4. **FFmpeg Streamer** maintains persistent RTMP connection to YouTube

## Monitoring & Troubleshooting

### Health Checks
```bash
# Overall pipeline health
curl http://your-domain:8000/debug/pipeline

# Broadcast controller status
curl http://your-domain:8001/status

# Temporal workflows
curl http://your-domain:8080  # Web UI
```

### Common Issues

#### Videos Not Streaming
```bash
# Check video generation
curl http://your-domain:8000/debug/files

# Check broadcast queue
curl http://your-domain:8001/status

# Force video generation
curl -X POST http://your-domain:8000/channels/1/workflow/trigger \
  -H "Content-Type: application/json" \
  -d '{"immediate": true}'
```

#### Stream Key Issues
```bash
# Check YouTube connectivity
python -c "
import socket
try:
    socket.create_connection(('a.rtmp.youtube.com', 1935), timeout=5)
    print('✅ YouTube RTMP reachable')
except:
    print('❌ YouTube RTMP blocked')
"
```

#### Service Logs
```bash
# All services
docker compose logs

# Specific service
docker compose logs backend
docker compose logs backend-worker
docker compose logs temporal
```

## Scaling Considerations

### High Traffic
- Increase Temporal worker replicas: `docker compose up -d --scale backend-worker=3`
- Add Redis for caching: Configure in `docker-compose.yml`
- Use external PostgreSQL for better performance

### Storage Management
- Videos auto-cleanup after 5 files (configurable in `monitor.py`)
- Monitor disk usage: `docker system df`
- External storage: Mount `/app/videos` to persistent volume

## Security Checklist

- [ ] Change default database password
- [ ] Use strong API keys
- [ ] Configure firewall (only expose necessary ports)
- [ ] Enable HTTPS with reverse proxy (nginx/caddy)
- [ ] Regular security updates: `docker compose pull && docker compose up -d`
- [ ] Monitor logs for suspicious activity

## Backup Strategy

### Database Backup
```bash
# Daily backup script
docker exec vartapravah_postgres_1 pg_dump -U root temporal > backup_$(date +%Y%m%d).sql
```

### Video Content
```bash
# Backup generated videos
docker run --rm -v vartapravah_video_data:/data -v $(pwd):/backup alpine tar czf /backup/videos_backup.tar.gz -C /data .
```

## Update Process

### Rolling Updates
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose build
docker compose up -d

# Verify
curl http://your-domain:8000/health
```

### Zero-Downtime Updates
```bash
# Update with temporary service
docker compose up -d backend-new
# Wait for health check
docker compose stop backend
docker compose rename backend backend-old
docker compose rename backend-new backend
docker compose up -d backend
docker compose rm backend-old
```

## Performance Tuning

### FFmpeg Optimization
- Video bitrate: 2500k (configured in `streamer.py`)
- Preset: veryfast (balance between speed/quality)
- Tune: zerolatency (for live streaming)

### Temporal Configuration
- Activity timeouts: 15 minutes for video generation
- Retry policies: Automatic for failed activities
- Worker concurrency: 1 per container (configurable)

## Support

For issues:
1. Check diagnostics: `python backend/diagnose_pipeline.py`
2. Review logs: `docker compose logs`
3. Check Temporal UI for workflow status
4. Verify YouTube stream key validity

## Recent Fixes Applied

- ✅ Fixed FFmpeg audio filter invalid output pad
- ✅ Added fallback promo generation
- ✅ Improved video queueing with retry logic
- ✅ Enhanced broadcast controller monitoring
- ✅ Added comprehensive diagnostics

The system should now reliably generate and stream news videos to YouTube every 15 minutes.