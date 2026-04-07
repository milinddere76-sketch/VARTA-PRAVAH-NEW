FROM python:3.10-slim

# System bindings to guarantee FFmpeg PiP functionality
RUN apt-get update && apt-get install -y ffmpeg curl bash procps fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Optimization: Copy requirements first to utilize Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Hard copy all modules, assets, and AI scripts
COPY . .

# Native port for FastAPI binding
EXPOSE 8000

# Default command (will be overridden by docker-compose for workers)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
