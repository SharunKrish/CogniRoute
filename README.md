# CogniRoute — Real-Time AI Customer Request Routing System

CogniRoute is an internal operations queue system that automatically routes customer inquiries into workflow queues. It receives messages from forms, emails, or WhatsApp, classifies them using AI in the background, logs audit history, and displays live updates on a glassmorphic admin dashboard.

Designed for SDE / AI Systems / Full-Stack assessments.

---

## 🔗 Live Demo & Project Links

* **🎥 Demo Video (YouTube)**: [Watch the Walkthrough](https://youtu.be/VnFmczS_EHQ)
* **🌐 Live Frontend App**: [cogni-route.vercel.app](https://cogni-route.vercel.app/)
* **🤖 Telegram Integration**: [Interact with @srk_s22_bot](https://t.me/srk_s22_bot)
* **⚡ Live Backend API**: [cogniroute.onrender.com](https://cogniroute.onrender.com/)

---

## Technical Architecture Overview

CogniRoute implements a non-blocking queue architecture:

```
[Customer Request]
       │ (REST / Webhook)
       ▼
 [Django REST API] ──(Saves immediately with status="queued")
       │
       ├──(Dispatches Task) ──► [Celery Worker]
       │                              │ (Queries AI Provider)
       │                              ▼
       │                       [Gemini / Mock AI]
       │                              │ (Structured output)
       │                              ▼
       │                        [Updates DB & snap fields]
       │                              │
       │                        (Publishes Event)
       │                              ▼
 [Daphne ASGI WebSockets] ◄── [Redis Channels]
       │
       ▼ (Live Update UI)
[Admin SPA Dashboard]
```

Detailed design explanations can be found in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Deliverables Checklist

- [x] **Backend REST API**: Complete JWT authentication, customer request queues, internal notes threads, and audit history.
- [x] **Database Schema**: Structured relations with indexing and a distinct AI classification audit table.
- [x] **Async Pipeline**: Background Celery task processing with transaction safety blocks.
- [x] **AI Classifier**: Replaceable Provider interface. Built-in `MockAIProvider` heuristics and `GeminiProvider` structured output.
- [x] **Real-time Engine**: WebSocket connection handling with custom JWT parameter authentication.
- [x] **Glassmorphic UI**: Dashboard view featuring table filters, searches, loading indicators, and animated `<dialog>` forms.
- [x] **Inbound Webhook**: Secured with SHA256 HMAC verification.
- [x] **Docker Compose**: Pre-configured services setup.
- [x] **Test Coverage**: 12 automated unit tests covering views, auth, and heuristics.
- [x] **Deployment Config**: Render configuration blueprints.

---

## Quick Start (Local Run)

### Prerequisites
- Python 3.12+
- Redis (running locally on port 6379)

### 1. Configure Python Environment
Navigate to the `server/` directory:
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Create a `.env` file in the `server/` folder (or copy `.env.example`):
```ini
SECRET_KEY=dev-secret-key-123456
DEBUG=True
AI_PROVIDER=mock
REDIS_URL=redis://127.0.0.1:6379/0
WEBHOOK_SECRET=cognifyr-secret-token-123
# Optional: Add to use real AI
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Initialize & Seed Database
Ensure your local Redis server is running (`redis-server`). Then execute:
```bash
python manage.py migrate
python seed_db.py
```
*Seeding creates two accounts:*
- **Admin**: user `admin` / pass `admin123`
- **Agent**: user `agent` / pass `agent123`

### 4. Start Servers
Start the Django ASGI development server:
```bash
python manage.py runserver
```

In a new terminal tab (with virtualenv activated), start the Celery background worker:
```bash
celery -A cogniroute worker --loglevel=info
```

Open [http://localhost:8000/](http://localhost:8000/) in your browser and log in with seeded credentials.

---

## Run with Docker Compose

To spin up the entire multi-container architecture (PostgreSQL, Redis, Daphne Web, and Celery Worker) with one command:

```bash
docker-compose up --build
```
The Django service waits for Postgres/Redis to be healthy, automatically runs migrations, seeds the database, and exposes the app on [http://localhost:8000/](http://localhost:8000/).

---

## Test Suite
To run the automated tests verifying API views, webhook safety, and heuristics:
```bash
cd server
python manage.py test
```

---

## Supplementary Documentation

- [Architecture Design Details (ARCHITECTURE.md)](ARCHITECTURE.md)
- [REST API Endpoints Guide (API_DOCS.md)](API_DOCS.md)
- [Technical Tradeoffs & Next Steps (TRADEOFFS.md)](TRADEOFFS.md)
