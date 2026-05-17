# 🛠️ Varta Pravah - Installation & Setup Guide

This guide covers the setup for the **2-Server Architecture** (Hetzner + Oracle Cloud).

---

## 🏗️ Server 1: Hetzner (AI processing)

### 1. Requirements
- Docker & Docker Compose
- 8GB+ RAM (Recommended)
- Oracle SSH Key (`ssh-key-2026-04-23.key`) placed in the root folder.

### 2. Configuration
Edit the `.env` file (Personalized for your servers):
```bash
ORACLE_IP=161.118.173.23
HETZNER_IP=157.180.24.243
ORACLE_USER=ubuntu
YOUTUBE_RTMP_URL=rtmp://a.rtmp.youtube.com/live2/your_key
```

### 3. Launch & Workflow
1. **Start the factory**:
   ```bash
   docker compose -f docker-compose-hetzner.yml up -d --build
   ```
2. **Automatic Workflow**:
   - The system generates the Marathi news video.
   - **Upload Step**: It automatically executes `scp /app/output/final_bulletin_ID.mp4 ubuntu@ORACLE_IP:/home/ubuntu/videos/`.
   - **Cleanup**: It deletes the local file after successful transfer to save disk space.

---

## 📡 Server 2: Oracle Cloud (Streaming Relay)

You have two options to set up the Oracle node:

### Option A: Docker (Recommended)
This method is fully automated and uses the specialized `Dockerfile.streamer`.

1. **Launch**:
   ```bash
   docker compose -f docker-compose-oracle.yml up -d --build
   ```
2. **Result**:
   - RTMP Server: `rtmp://your_oracle_ip:1935/live`
   - HLS Monitor: `http://your_oracle_ip:8080/live/stream.m3u8`

### 1. Preparation (On Oracle Server)
Create the professional directory structure:
```bash
mkdir -p /home/ubuntu/videos/breaking /home/ubuntu/queue /home/ubuntu/backup /home/ubuntu/logs
chmod -R 777 /home/ubuntu/videos /home/ubuntu/queue /home/ubuntu/logs
```

### Option A: Docker (Recommended)

1. **Install NGINX RTMP**:
   ```bash
   sudo apt update
   sudo apt install -y nginx libnginx-mod-rtmp ffmpeg
   ```

2. **Configure RTMP**:
   Open `/etc/nginx/nginx.conf` and add the following at the bottom:
   ```nginx
   rtmp {
       server {
           listen 1935;
           chunk_size 4096;

           application live {
               live on;
               record off;

               # Push to YouTube
               push rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY;

               # Enable HLS for stability
               hls on;
               hls_path /var/www/hls;
               hls_fragment 3;
           }
       }
   }

   http {
       server {
           listen 8080;
           location /live {
               types {
                   application/vnd.apple.mpegurl m3u8;
                   video/mp2t ts;
               }
               root /var/www/hls;
           }
       }
   }
   ```

3. **Setup HLS Directory**:
   ```bash
   sudo mkdir -p /var/www/hls
   sudo chmod -R 777 /var/www/hls
   ```

4. **Restart**:
   ```bash
   sudo systemctl restart nginx
   ```

### 2. Auto-Stream Script (Manual Path)
To automatically play all videos uploaded from Hetzner, create the loop script:

1. **Create the script**:
   ```bash
   nano /home/ubuntu/stream_loop.sh
   ```
2. **Paste content**:
   ```bash
   #!/bin/bash
   VIDEO_DIR="/home/ubuntu/videos"
   while true
   do
     for file in $VIDEO_DIR/*.mp4
     do
       ffmpeg -re -stream_loop -1 -i "$file" \
       -c:v libx264 -preset veryfast -b:v 2500k \
       -c:a aac -b:a 128k \
       -f flv rtmp://localhost/live/stream
     done
   done
   ```
3. **Run in background**:
   ```bash
   chmod +x /home/ubuntu/stream_loop.sh
   nohup ./stream_loop.sh > stream.log 2>&1 &
   ```

### 3. NO STOP STREAM (Pro Playout Engine)
The professional way to handle 24/7 broadcasting is to use a dynamic playlist.

1. **Create the playout script**:
   ```bash
   nano /home/ubuntu/playout.sh
   ```
2. **Paste content**:
   ```bash
   #!/bin/bash
   PLAYLIST="/home/ubuntu/queue/playlist.txt"
   while true; do
     ffmpeg -re -f concat -safe 0 -i $PLAYLIST \
     -c:v libx264 -preset veryfast -b:v 2500k \
     -c:a aac -b:a 128k \
     -f flv rtmp://a.rtmp.youtube.com/live2/YOUR_KEY

     echo "⚠️ Restarting stream..." >> /home/ubuntu/logs/playout.log
     sleep 2
   done
   ```
3. **Initialize the playlist**:
   ```bash
   echo "ffconcat version 1.0" > /home/ubuntu/queue/playlist.txt
   echo "file '/home/ubuntu/videos/promo.mp4'" >> /home/ubuntu/queue/playlist.txt
   ```
4. **Run in background**:
   ```bash
   chmod +x /home/ubuntu/playout.sh
   nohup ./playout.sh &
   ```

### 4. DYNAMIC QUEUE SYSTEM (The Brain)
To automate the playlist updates, run the queue manager script:

1. **Create the queue manager**:
   ```bash
   nano /home/ubuntu/queue_manager.sh
   ```
2. **Paste content**:
   ```bash
   #!/bin/bash
   VIDEO_DIR="/home/ubuntu/videos"
   PLAYLIST="/home/ubuntu/queue/playlist.txt"
   while true; do
     echo "ffconcat version 1.0" > $PLAYLIST
     
     # 1. PRIORITY: Breaking news first
     for file in $VIDEO_DIR/breaking/*.mp4; do
       if [ -f "$file" ]; then echo "file '$file'" >> $PLAYLIST; fi
     done

     # 2. STANDARD: Regular news
     counter=0
     for file in $VIDEO_DIR/*.mp4; do
       if [ -f "$file" ]; then
         echo "file '$file'" >> $PLAYLIST
         ((counter++))
         if [ $((counter % 5)) -eq 0 ]; then
           echo "file '/home/ubuntu/videos/promo.mp4'" >> $PLAYLIST
         fi
       fi
     done

     # 3. ZERO-DOWNTIME SECRET
     echo "file '/home/ubuntu/videos/fallback.mp4'" >> $PLAYLIST

     sleep 10
   done
   ```
3. **Run in background**:
   ```bash
   chmod +x /home/ubuntu/queue_manager.sh
   nohup ./queue_manager.sh &
   ```

### 🚀 Oracle AUTO START (Final)
To launch the entire playout system in one go:
```bash
# Make all scripts executable
chmod +x /home/ubuntu/*.sh

# Start the Brain (Queue Manager)
nohup /home/ubuntu/queue_manager.sh > /home/ubuntu/logs/brain.log 2>&1 &

# Start the Engine (Playout)
nohup /home/ubuntu/playout.sh > /home/ubuntu/logs/engine.log 2>&1 &
```

---

## 📶 Network Configuration (Firewall)

Ensure the following ports are open on your Oracle Cloud Security List (Ingress Rules):
- **Port 22 (TCP)**: Required for `rsync` transfers from Hetzner.
- **Port 1935 (TCP)**: Required for RTMP streaming.
- **Port 8080 (TCP)**: Optional, for HLS monitoring.

---

## 🧹 Pro Security & Maintenance
1. **SSH Security**: Automated transfers from Hetzner use the SSH Identity Key (`ssh-key-2026-04-23.key`). Password authentication is not required and should be disabled for maximum security.
2. **Path Restriction**: The factory is restricted to uploading only into the `/home/ubuntu/videos/` directory.
3. **Auto-Cleanup**: To prevent disk exhaustion, the Oracle server automatically deletes bulletins older than 2 days. 
   
Add this to your crontab (`crontab -e`):
```bash
# Every midnight, delete news older than 2 days
0 0 * * * find /home/ubuntu/videos -type f -mtime +2 -delete
## 📊 Monitoring & Health Checks
To ensure your 24/7 broadcast is running smoothly, use these commands:

1. **System Resources (CPU/RAM)**:
   ```bash
   htop
   ```
2. **Live Stream Logs (Oracle)**:
   ```bash
   # Watch the engine in real-time
   tail -f /home/ubuntu/logs/playout.log
   ```
3. **Queue Brain Logs (Oracle)**:
   ```bash
   # Watch the playlist updates
   tail -f /home/ubuntu/logs/brain.log
   ```
4. **Hetzner Factory Status**:
   ```bash
   docker logs -f vartapravah-worker
   ```
