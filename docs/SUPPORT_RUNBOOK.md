# RoadSOS Tier-1 / Tier-2 Support & Operations Troubleshooting Runbook

**Target Audience**: Customer Support Specialists, Paramedic Dispatch Operators, Tier-1/2 Helpdesk  
**Release Version**: RoadSOS v1.0.0

---

## 1. Common User Problems & Troubleshooting Matrix

| Issue Category | Symptom | Root Cause | Resolution Procedure |
| :--- | :--- | :--- | :--- |
| **Authentication** | User sees *"Session Expired"* or HTTP 401 error | JWT access token expired (>15 mins) and refresh token invalid | Direct user to `/login`. Clear local storage if token corrupt: `localStorage.clear()` in browser console. |
| **Failed Triage Submission** | User receives *"Triage failed"* prompt | Invalid GPS coords (`lat/lng` out of bounds) or unprocessable input | Verify GPS permissions in device settings; advise user to select emergency location on map. |
| **Delayed Asynchronous Job** | Triage job stuck in `queued` status for > 30 seconds | High system load or worker process failure | SRE scales worker fleet. PWA client polls `/api/triage/jobs/{id}` automatically up to 60 seconds. |
| **Responder Queue Missing Case** | Paramedic dashboard does not list a newly submitted emergency | Incident status is not `pending` or assigned to another paramedic unit | Query responder queue API: `GET /api/responder/queue`. Check IDOR boundaries and filter settings. |
| **Offline SOS Sync Issue** | Emergency SOS submitted offline does not update server | Browser background sync pending or IndexedDB blocked | Ensure device reconnected to mobile data/Wi-Fi. PWA will auto-trigger `sos-sync` event upon network recovery. |

---

## 2. Paramedic & Emergency Dispatch Operations

1. **Queue Priority Sorting**:
   - `P1 (Critical)` cases appear at top of queue with red highlight.
   - `P2 (Serious)` cases follow with orange highlight.
   - `P3 (Moderate)` cases display yellow highlight.
   - `P4 (Minor)` cases display green highlight.
2. **Job Assignment & Resolution Flow**:
   - Paramedic clicks **Assign Unit** → Job status transitions to `assigned`.
   - On-scene arrival → Click **Mark In Progress** → Job status transitions to `in_progress`.
   - Patient transport complete → Click **Mark Resolved** → Job status transitions to `resolved`.

---

## 3. Emergency Manual Fallback Procedure

If the automated AI triage engine experiences an unexpected outage:
1. **Fallback Triage Form**: Direct citizens to use the manual triage assessment form available on `AITriagePage.jsx`.
2. **Direct Dispatch Backup**: Emergency operators can manually dispatch units via `GET /api/hospitals/nearest` and direct radio communication.
