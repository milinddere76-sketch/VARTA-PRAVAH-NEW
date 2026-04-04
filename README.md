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
3. Copy `.env.example` to `.env` and fill in your API keys.
4. Run the worker: `python -m temporal.worker`
5. Run the API: `uvicorn main:app --reload`

### 3. Frontend Setup
1. Navigate to `/frontend`.
2. `npm install`
3. `npm run dev`

### 4. Streaming Engine
The `streamer.py` script is managed by the backend or can be run manually for testing:
`python streamer.py`

## 🧩 Tech Stack
- **Next.js**: Modern dashboard with Tailwind CSS.
- **Temporal**: Robust workflow management for long-running video generation tasks.
- **Sync Labs**: Cost-effective lip-syncing for fixed anchors.
- **FastAPI**: High-performance asynchronous API layer.
