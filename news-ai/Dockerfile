FROM python:3.10-slim

# Install FFMpeg and OS prerequisites
RUN apt-get update && apt-get install -y ffmpeg curl bash && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
RUN pip install requests groq gtts python-dotenv pillow

# Copy logic
COPY . /app

# Make the executable scripts runnable
RUN chmod +x stream.sh entrypoint.sh

# Start the dual-process architecture
CMD ["./entrypoint.sh"]
