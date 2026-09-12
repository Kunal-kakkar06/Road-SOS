# RoadSOS Responder Workflow Audit & Priority Matrix

**Effective Date**: September 11, 2026  

---

## Responder Dispatch Workflow Steps

1. **Authentication & Authorization**: Paramedics and first responders authenticate via `/api/auth/login` to obtain authorized bearer tokens.
2. **Emergency Queue Visibility**: Responders query active emergency triage records sorted by severity level (`Critical` -> `High` -> `Moderate` -> `Low`).
3. **Job Assignment & Status Transitions**: Active emergency cases transition through lifecycle states:
   `pending` ──► `processing` ──► `completed` / `dispatched`
4. **Responder Dispatch & Ambulance Routing**: Nearest ambulance and hospital routing metadata is attached to high/critical severity incidents.

---

## Priority Ordering & Response Matrix

| Emergency Severity | Priority Level | Target Response Window | Automated Dispatch Trigger |
| :--- | :---: | :---: | :--- |
| **Critical** | Priority 1 (Immediate) | < 5 minutes | Immediate SMS alert & nearest ambulance dispatch |
| **High** | Priority 2 (Urgent) | < 10 minutes | Priority responder queue placement |
| **Moderate** | Priority 3 (Standard) | < 20 minutes | Standard dispatch queue placement |
| **Low** | Priority 4 (Non-Urgent) | < 45 minutes | Self-care advice & local clinic recommendation |
