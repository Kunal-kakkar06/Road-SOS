# RoadSOS Production System Handover Manifest

**Handover Date**: September 11, 2026  
**System Version**: RoadSOS v1.0.0  
**Target Platform**: RoadSOS Emergency Triage & Dispatch Platform

---

## 1. System Asset & Resource Inventory

| Asset Name | Location / Path | Purpose & Description |
| :--- | :--- | :--- |
| **Backend API Engine** | `backend/` | FastAPI async REST API service (`main:app`) |
| **Distributed ML Worker** | `backend/worker.py` | PostgreSQL queue worker engine |
| **Frontend PWA Web App** | `frontend/` | React 18 + Vite PWA frontend (`dist/`) |
| **ML Model Artifact** | `backend/models/fusion_triage.pkl` | XGBoost triage model (SHA-256: `e014884ed8...`) |
| **Database Migrations** | `backend/alembic/` | Alembic PostgreSQL migrations (Head: `c3d4e5f6a7b8`) |
| **Operational Manuals** | `docs/` | 20+ comprehensive SRE, ML, security & support runbooks |

---

## 2. Production Environment Endpoint URLs

- **Frontend Application**: `http://localhost:5173` (Local Dev) / `https://roadsos.app` (Production)
- **Backend REST API**: `http://localhost:8000` (Local Dev) / `https://api.roadsos.app` (Production)
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **Prometheus Metrics**: `http://localhost:8000/metrics`
- **Health Check Endpoint**: `http://localhost:8000/health`
