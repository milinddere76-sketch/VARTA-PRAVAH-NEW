#!/bin/bash

# Varta Pravah - MASTER INITIALIZATION SCRIPT
echo "🚀 [INIT] Starting Varta Pravah Playout Node..."

# 1. Setup Environment
if [ -n "$YOUTUBE_RTMP_URL" ]; then
    echo "✅ [INIT] Using YOUTUBE_RTMP_URL directly from environment."
    FINAL_RTMP_URL="$YOUTUBE_RTMP_URL"
else
    echo "🔧 [INIT] Assembling RTMP URL from default stream key..."
    STREAM_KEY=${YOUTUBE_STREAM_KEY:-"qcu7-xesd-m4sv-9zvv-e335"}
    BASE_URL="rtmp://a.rtmp.youtube.com/live2/"
    [[ "$BASE_URL" != */ ]] && BASE_URL="$BASE_URL/"
    FINAL_RTMP_URL="${BASE_URL}${STREAM_KEY}"
fi

# Export for playout.sh and envsubst
export YOUTUBE_RTMP_URL="$FINAL_RTMP_URL"

# 1a. Setup Facebook Environment
if [ -n "$FACEBOOK_RTMP_URL" ]; then
    echo "✅ [INIT] Using FACEBOOK_RTMP_URL directly from environment."
    FINAL_FB_RTMP_URL="$FACEBOOK_RTMP_URL"
elif [ -n "$FACEBOOK_STREAM_KEY" ]; then
    echo "🔧 [INIT] Assembling Facebook RTMP URL from stream key..."
    BASE_FB_URL="rtmp://live-api-s.facebook.com:80/rtmp/"
    [[ "$BASE_FB_URL" != */ ]] && BASE_FB_URL="$BASE_FB_URL/"
    FINAL_FB_RTMP_URL="${BASE_FB_URL}${FACEBOOK_STREAM_KEY}"
else
    FINAL_FB_RTMP_URL=""
fi
export FACEBOOK_RTMP_URL="$FINAL_FB_RTMP_URL"

# VERIFICATION: Show masked URL to confirm fusion worked
MASKED_URL=$(echo "$YOUTUBE_RTMP_URL" | sed 's/live2\/.*/live2\/XXXXX/')
echo "🔗 [INIT] Target Broadcast URL: $MASKED_URL"

if [ -n "$FACEBOOK_RTMP_URL" ]; then
    MASKED_FB_URL=$(echo "$FACEBOOK_RTMP_URL" | sed 's/rtmp\/.*/rtmp\/XXXXX/')
    echo "🔗 [INIT] Target Facebook Broadcast URL: $MASKED_FB_URL"
fi

mkdir -p /home/ubuntu/queue /home/ubuntu/logs /home/ubuntu/videos/breaking /app/assets
chmod -R 777 /app/assets /home/ubuntu/queue /home/ubuntu/logs /home/ubuntu/videos

# 1b. AUTO-RESTORE: If images are missing from the volume mount, restore from internal backup
if [ -d "/app/backup_assets" ] && [ $(ls /app/assets/promo_*.png 2>/dev/null | wc -l) -eq 0 ]; then
    echo "📦 [INIT] Restoring branding assets from internal backup..."
    cp /app/backup_assets/*.png /app/assets/ 2>/dev/null || true
    cp /app/backup_assets/*.mp4 /app/assets/ 2>/dev/null || true
    chmod -R 777 /app/assets
fi

# 2. Configure Nginx (Copy template)
cp /etc/nginx/nginx.conf.template /etc/nginx/nginx.conf

nginx
echo "✅ [INIT] Nginx RTMP server online."




# 3. Generate Widescreen 16:9 Premium Standby Promo Video
echo "🎬 [INIT] Rendering widescreen 16:9 premium standby promo..."
PROMO_BG="/app/assets/promo_bg.png"
STUDIO_BG="/app/assets/studio_bg.png"
LOGO_FILE="/app/assets/logo.png"
PROMO_OUT="/app/assets/promo.mp4"

if [ -f "$PROMO_BG" ]; then
    echo "🎨 [INIT] Composing widescreen 16:9 promo loop using user-provided slide: $PROMO_BG"
    ffmpeg -y -loop 1 -i "$PROMO_BG" \
      -f lavfi -i "sine=f=60:d=30,aecho=0.8:0.88:60:0.4" \
      -filter_complex "[0:v]scale=1280:1280,crop=1280:720,format=yuv420p[v]; [1:a]arealtime,aloop=loop=25:size=44100[a]" \
      -map "[v]" -map "[a]" -c:v libx264 -preset fast -crf 20 -r 25 -pix_fmt yuv420p -c:a aac -shortest -t 30 "$PROMO_OUT"
elif [ -f "$STUDIO_BG" ] && [ -f "$LOGO_FILE" ]; then
    echo "🎨 [INIT] Composing widescreen 16:9 promo loop with fallback branding overlay..."
    ffmpeg -y -loop 1 -i "$STUDIO_BG" \
      -loop 1 -i "$LOGO_FILE" \
      -f lavfi -i "sine=f=60:d=30,aecho=0.8:0.88:60:0.4" \
      -filter_complex "[0:v]scale=1280:1280,crop=1280:720[bg]; [1:v]scale=180:180[logo]; [bg][logo]overlay=50:50[vbg]; [vbg]drawtext=text='VARTA PRAVAH':fontcolor=white:fontsize=95:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:borderw=5:bordercolor=0x00d2ff:x=(w-tw)/2:y=(h-th)/2-40,drawtext=text='वार्ता प्रवाह':fontcolor=0x00d2ff:fontsize=65:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:borderw=2:bordercolor=black:x=(w-tw)/2:y=(h-th)/2+60,format=yuv420p[v]; [2:a]arealtime,aloop=loop=25:size=44100[a]" \
      -map "[v]" -map "[a]" -c:v libx264 -preset fast -crf 20 -r 25 -pix_fmt yuv420p -c:a aac -shortest -t 30 "$PROMO_OUT"
else
    echo "⚠️ [WARN] Missing key branding assets. Generating backup widescreen blue screen..."
    ffmpeg -y -f lavfi -i color=c=0x1a1a2e:s=1280x720:d=30 -f lavfi -i "sine=f=220:d=30" \
      -vf "drawtext=text='VARTA PRAVAH':fontcolor=white:fontsize=95:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:borderw=5:bordercolor=0x00d2ff:x=(w-tw)/2:y=(h-th)/2-40,drawtext=text='वार्ता प्रवाह':fontcolor=0x00d2ff:fontsize=65:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:borderw=2:bordercolor=black:x=(w-tw)/2:y=(h-th)/2+60" \
      -c:v libx264 -preset fast -pix_fmt yuv420p -c:a aac -shortest -y "$PROMO_OUT"
fi

# 4. Sync Fallback
cp "$PROMO_OUT" /app/assets/fallback.mp4
chmod 777 /app/assets/promo.mp4 /app/assets/fallback.mp4
echo "✅ [INIT] Premium 16:9 Standby Promo deployed."

# 5. Launch the Brain (Queue Manager)
echo "🧠 [INIT] Starting the Brain (Queue Manager)..."
/app/queue_manager.sh &

# 6. Launch the Playout Engine
echo "📺 [INIT] Handing over to Playout Engine..."
/app/playout.sh
