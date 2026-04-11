# VartaPravah: 24x7 AI News Channel SaaS

VartaPravah is a fully automated AI news broadcasting platform focusing on regional languages (Marathi). It generates news scripts, creates AI-driven anchor videos, and streams them 24/7 to YouTube.

## 🏗️ Architecture

- **Backend**: FastAPI (Python)
- **Workflow Engine**: Temporal.io (Orchestration)
- **Streaming**: FFmpeg (RTMP to YouTube)
- **Database**: PostgreSQL (PostgreSQL)
- **Frontend**: Next.js (Dashboard)
- **AI Services**: Sync Labs (Lip-Sync), OpenAI/Gemini (Scripts/TTS)

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+ 
- Node.js 18+ 
- Temporal Server (Local or Cloud)
- FFmpeg installed in system PATH

### 2. Backend Setup
1. Navigate to `/backend`.
2. `pip install -r requirements.txt`
3. Copy `backend/.env.example` to `backend/.env` and fill in your API keys.
4. Run the worker: `python -m streaming_engine.worker`
5. Run the API: `uvicorn main:app --reload`

### 2a. Environment Variables
- `DATABASE_URL`: PostgreSQL connection string for production or Docker.
- `SQLITE_URL`: local SQLite fallback for development when PostgreSQL is unavailable.
- `TEMPORAL_ADDRESS`: Temporal server host and port, e.g. `localhost:7233`.
- `GROQ_API_KEY`, `WORLD_NEWS_API_KEY`, `YOUTUBE_STREAM_KEY`: service API keys.

> If PostgreSQL is unreachable during startup, the backend will automatically fall back to the local SQLite database specified by `SQLITE_URL` or `backend/dev.db`.

### 3. Frontend Setup
1. Navigate to `/frontend`.
2. `npm install`
3. `npm run dev`

### 4. Streaming Engine
The `streamer.py` script is managed by the backend or can be run manually for testing:
`python streamer.py`

### 5. Production Deployment
- Use `docker compose up -d --build` on the target server.
- Ensure `backend/.env` is populated with production values and keep it out of Git.
- Remove or do not set `SQLITE_URL` in production; use PostgreSQL via `DATABASE_URL`.
- Set `TEMPORAL_ADDRESS=temporal:7233`, and ensure `temporal` and `postgres` services are reachable from `backend`.
- Open only the public ports you need: `3000`, `8000`, `8088`, and `7233` as required.
- For Coolify, use the project Docker Compose file and configure env vars in the platform UI.

## 🧩 Tech Stack
- **Next.js**: Modern dashboard with Tailwind CSS.
- **Temporal**: Robust workflow management for long-running video generation tasks.
- **Sync Labs**: Cost-effective lip-syncing for fixed anchors.
- **FastAPI**: High-performance asynchronous API layer.
