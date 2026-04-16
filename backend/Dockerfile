# Use a more specific version for consistency
FROM python:3.11-slim

# Install system dependencies with cache mount
ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    fonts-noto-hinted \
    fonts-dejavu-core \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    libz-dev \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and setup script first for better caching
COPY requirements.txt setup_pip.sh ./
RUN --mount=type=cache,target=/root/.cache/pip \
    chmod +x setup_pip.sh && ./setup_pip.sh

# Copy the rest of the backend code
COPY . .

# Ensure videos directory exists
RUN mkdir -p /app/videos

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
