# RoadSOS Security Analytics & Threat Monitoring Policy

**Policy Version**: v1.0.0  
**Target Scope**: Authentication Security, IDOR Protection, Rate Limiting, Threat Analytics

---

## 1. Security Event Monitoring Metrics

| Security Dimension | Monitored Metric | Target Threshold | Incident Action |
| :--- | :--- | :---: | :--- |
| **Auth Failures** | Repeated failed login attempts | < 5 attempts / IP / 5 min | Trigger IP rate-limiting block (HTTP 429) |
| **IDOR Attempts** | Cross-user job query attempts | **0 allowed** | Block request, log security alert, raise alert |
| **Input Validation** | Malformed / SQLi payload submissions | **0 allowed** | Reject via Pydantic schema validation (HTTP 422) |
| **Secret Scanning** | Client JS bundle secret leaks | **0 secrets allowed** | **BLOCK BUILD** in CI/CD pipeline |

---

## 2. Threat Mitigation Recommendations
- `KEEP`: Centralized JWT authentication & IDOR ownership verification.
- `MONITOR`: Prometheus security metrics `auth_failures_total` and `idor_blocked_total`.
