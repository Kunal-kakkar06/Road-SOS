# RoadSOS Developer Onboarding & Technical Handoff Guide

**Target Audience**: Software Engineers, ML Engineers, Backend/Frontend Developers  
**Release Version**: RoadSOS v1.0.0  
**Repository Path**: `ROADSOS/`

---

## 1. System Architecture Overview

RoadSOS is an AI-powered emergency triage and paramedic dispatch application featuring:
- **FastAPI Backend**: Async REST API handling authentication, sync triage, async job queueing, and responder dispatch.
- **XGBoost + NLP + SHAP Engine**: High-speed hybrid ML model producing severity ratings (`P1`-`P4`), numerical severity scores (`0.0`-`1.0`), textual assessments, actionable instructions, and SHAP explainability factors.
- **PostgreSQL Database**: Relational storage for users, triage jobs, triage events, and responder dispatch queues. Uses `FOR UPDATE SKIP LOCKED` for race-safe worker job claiming.
- **Distributed Worker Fleet**: Background Python workers (`worker.py`) polling PostgreSQL for asynchronous triage processing.
- **React Vite PWA**: Responsive frontend supporting offline triage estimation, Service Worker caching, and background sync.

---

## 2. Local Development Environment Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (optional for full stack)

### Quickstart Setup Steps

```bash
# 1. Clone & enter repository
git clone https://github.com/Kunal-kakkar06/ROADSOS.git
cd ROADSOS

# 2. Setup Backend Virtual Environment
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Initialize Database Migrations
alembic upgrade head

# 4. Run Backend API
uvicorn main:app --reload --port 8000

# 5. Start Background Worker (in separate terminal)
python3 worker.py

# 6. Setup & Run Frontend PWA (in separate terminal)
cd ../frontend
npm install
npm run dev
```

---

## 3. Running the Test Suite

The project includes an extensive Pytest test suite covering unit, security, integration, ML, and UX requirements:

```bash
cd backend
source venv/bin/activate

# Run complete test suite (300 tests)
pytest tests/ -v

# Run physical step verification script
python3 test_step36_handoff.py
```

---

## 4. Repository Directory Structure

```
ROADSOS/
├── backend/
│   ├── ai/                      # ML pipeline, feature extraction, NLP & SHAP engines
│   │   ├── feature_engine/      # 10-feature extraction & NLP scoring
│   │   ├── decision/            # Decision rules & threshold mapping
│   │   └── models/              # Base model wrappers
│   ├── alembic/                 # Database migrations (Alembic)
│   ├── dependencies/            # FastAPI dependencies (auth, DB sessions)
│   ├── models/                  # SQLAlchemy DB models & ML pickle (`fusion_triage.pkl`)
│   ├── routers/                 # API routers (auth, triage, responder, incident)
│   ├── services/                # Business logic & Job Manager
│   ├── tests/                   # Pytest automated test suite (300 tests)
│   ├── main.py                  # FastAPI application entry point
│   ├── worker.py                # Distributed background worker
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── public/                  # Static PWA assets & Service Worker (`sw.js`)
│   ├── src/
│   │   ├── components/          # Reusable UI components (`SeverityResult.jsx`)
│   │   ├── pages/               # React view pages (`AITriagePage.jsx`, `ResponderQueue.jsx`)
│   │   ├── services/            # API & PWA services (`offlineSOS.js`)
│   │   ├── App.jsx              # Main React routing & layout
│   │   └── main.jsx             # React entry point & HTTP 401 interceptor
│   └── package.json             # Frontend dependencies
└── docs/                        # Project documentation & operational handoff manuals
```

---

## 5. Guidelines for Safely Adding Future Features

1. **Preserve ML Invariants**: Never alter the 10-feature ordering or modify `fusion_triage.pkl` without updating the release manifest checksum.
2. **Database Migrations**: Always generate schema changes via `alembic revision --autogenerate -m "description"` and verify backward compatibility.
3. **API Contracts**: Ensure request/response schemas in `schemas.py` retain backward compatibility for existing PWA clients.
4. **Test Coverage**: Every new endpoint or service MUST include corresponding Pytest tests in `backend/tests/ai/`.
