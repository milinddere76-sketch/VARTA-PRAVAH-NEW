FROM python:3.11-slim

# Install system dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    fonts-noto-hinted \
    fonts-dejavu-core \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    libz-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://pypi.org/simple --default-timeout=1000 --retries 20 -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Ensure videos directory exists
RUN mkdir -p /app/videos

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
