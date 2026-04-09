FROM python:3.10-slim

# Prevent Python buffering issues
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies (clean + stable)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    bash \
    procps \
    fonts-dejavu-core \
    fonts-noto-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Upgrade pip (IMPORTANT FIX)
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# 🔥 SAFE COPY (prevents build crash if files missing)
RUN cp -r *.mp4 /app/ 2>/dev/null || true
RUN cp -r *.jpg /app/ 2>/dev/null || true
RUN cp -r *.png /app/ 2>/dev/null || true

# Expose FastAPI port
EXPOSE 8000

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]