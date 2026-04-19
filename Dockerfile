FROM python:3.11-slim

LABEL Name="vartapravah" Version="0.0.1"

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    netcat-openbsd \
    procps \
    fonts-noto-hinted \
    fonts-noto-extra \
    fontconfig \
    fonts-dejavu-core \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    libz-dev \
    libpq-dev \
    gcc \
    python3-dev \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements and install dependencies
COPY backend/requirements.txt backend/setup_pip.sh ./
RUN chmod +x setup_pip.sh && ./setup_pip.sh

# Copy backend source
COPY backend ./

RUN mkdir -p /app/videos

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
