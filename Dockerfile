FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    libz-dev \
    && pip install --no-cache-dir -r requirements.txt

CMD ["python", "worker.py"]