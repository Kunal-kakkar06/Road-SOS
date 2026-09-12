# RoadSOS Data Governance, Privacy & PHI/PII Audit Report

**Audit Date**: September 11, 2026  
**Target Platform**: RoadSOS Emergency Triage & Dispatch Platform  
**Release Version**: RoadSOS v1.0.0 (Production Release Candidate)  
**Governance Status**: 🟢 **100% COMPLIANT (PHI/PII SECURED & BOUNDED)**

---

## 1. PHI / PII Data Inventory Matrix

| Data Category | Attributes / Fields | Privacy Classification | Storage Location | Retention & Anonymization Policy |
| :--- | :--- | :---: | :--- | :--- |
| **User Identity** | `email`, `hashed_password`, `full_name`, `phone_number` | **PII (High)** | PostgreSQL (`users` table) | Retained during active account. Soft-delete + hash anonymization on account deletion. |
| **Medical Profile** | `allergies`, `blood_type`, `emergency_contacts`, `preexisting_conditions` | **PHI (High)** | PostgreSQL (`medical_profiles` table) | Encrypted at rest. Isolated via strict user ownership queries. |
| **Emergency Triage** | `gps_lat`, `gps_lng`, `symptoms_text`, `audio_path`, `image_path` | **PHI / Location** | PostgreSQL (`triage_jobs`, `triage_events`) & MinIO | Retained 90 days for operational audit. Offsite backup archived after 90 days. |
| **Dispatch Events** | `assigned_paramedic_id`, `hospital_id`, `status`, `timestamps` | **Operational** | PostgreSQL (`triage_events`) | Permanent immutable log for medical dispatch audit compliance. |

---

## 2. Privacy & Access Boundaries

1. **Zero Unauthenticated Access**: Public endpoints restricted to `/health`, `/metrics`, and `/api/auth/*`. All triage, medical, and history endpoints require valid JWT authentication.
2. **Strict Cross-Tenant IDOR Isolation**: Users can query ONLY their own `user_id` records. Paramedics can access assigned queue items.
3. **Database & MinIO Encryption**: Database connections utilize SSL/TLS (`sslmode=require`), and S3 storage objects are encrypted at rest via AES-256.
4. **Log Redaction**: Credentials (`password`, `jwt`, `token`, `secret`) are scrubbed from server logs prior to output.

---

## 3. Data Deletion & Anonymization Verification

- **User Right-to-be-Forgotten**: Deleting a user account sets `is_active=False`, redacts `email` to `anonymized_<hash>@roadsos.internal`, and deletes associated sensitive medical profiles.
- **Log Retention**: Server logs rotated daily with 30-day retention ceiling.
