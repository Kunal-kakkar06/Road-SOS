# RoadSOS Frontend ↔ Backend API Contract Matrix

**Effective Date**: September 11, 2026  

---

## Production API Endpoint Contracts

| Endpoint Path | HTTP Method | Auth Required | Request Payload | Response Contract | Error Codes |
| :--- | :---: | :---: | :--- | :--- | :---: |
| `/api/auth/register` | `POST` | No | `{name, email, password, confirm_password}` | `{id, name, email}` | 400, 422 |
| `/api/auth/login` | `POST` | No | `{email, password}` | `{access_token, token_type}` | 400, 401, 422 |
| `/api/triage` | `POST` | Yes | `{symptoms, age, heart_rate, latitude, longitude}` | `{severity_level, severity_score, assessment, actions, shap_values}` | 401, 422 |
| `/api/triage/async` | `POST` | Yes | `{symptoms, age, heart_rate, latitude, longitude}` | `{job_id, status="pending"}` | 401, 422, 429 |
| `/api/triage/jobs/{job_id}` | `GET` | Yes | Path parameter `job_id` | `{job_id, status, result}` | 401, 403, 404 |
| `/api/triage/history` | `GET` | Yes | Query parameters | List of historical triage objects | 401 |
| `/health` | `GET` | No | None | `{status="ok", service, app_version}` | None |
| `/api/ready` | `GET` | No | None | `{status="ready", checks}` | 503 |
| `/metrics` | `GET` | No | None | Prometheus text format | None |
