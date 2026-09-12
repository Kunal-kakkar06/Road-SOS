# RoadSOS RBAC & Least-Privilege Access Control Audit

**Audit Date**: September 11, 2026  
**Release Version**: RoadSOS v1.0.0  
**Audit Status**: 🟢 **100% RBAC & LEAST-PRIVILEGE COMPLIANT**

---

## 1. Endpoint Authorization Matrix

| Endpoint URI | HTTP Method | Required Role | Unauthenticated | Citizen User | Responder / Paramedic | Admin |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `/health` | GET | Public | **ALLOW** | **ALLOW** | **ALLOW** | **ALLOW** |
| `/api/auth/login` | POST | Public | **ALLOW** | **ALLOW** | **ALLOW** | **ALLOW** |
| `/api/triage` | POST | Citizen | 401 | **ALLOW** | **ALLOW** | **ALLOW** |
| `/api/triage/jobs/{id}` | GET | Owner | 401 | **ALLOW (Owner)** | 403 (Non-Owner) | **ALLOW** |
| `/api/responder/queue` | GET | Paramedic | 401 | 403 | **ALLOW** | **ALLOW** |
| `/api/responder/assign` | POST | Paramedic | 401 | 403 | **ALLOW** | **ALLOW** |
| `/api/admin/dashboard` | GET | Admin | 401 | 403 | 403 | **ALLOW** |

---

## 2. Infrastructure & Service Separation

1. **API vs Worker Separation**: Worker process (`worker.py`) has zero direct HTTP access endpoints; interacts strictly with PostgreSQL queue via `FOR UPDATE SKIP LOCKED`.
2. **Database Permissions**: `roadsos` DB role restricted to application schema; lacks `SUPERUSER` privileges.
