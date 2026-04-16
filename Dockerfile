FROM python:3.10-slim

WORKDIR /app

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    libz-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefer-binary -r requirements.txt

# Copy the rest of the code
COPY . .

CMD ["python", "worker.py"]