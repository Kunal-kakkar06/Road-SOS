# RoadSOS Step 19 — Off-Site Backup Replication, Immutability & Final Production Hardening

## 1. Overview & Architecture

RoadSOS implements enterprise-grade, provider-independent off-site backup replication to S3-compatible object storage (AWS S3, MinIO, Cloudflare R2, Google Cloud Storage). 

```text
+-------------------+      pg_dump       +----------------------------+
|  PostgreSQL 15    |  ----------------> | Local Snapshot Backup      |
|  Database Host    |                    | roadsos_backup_*.sql.gz    |
+-------------------+                    +----------------------------+
                                                       |
                                            SHA-256 Checksum Manifest
                                                       |
                                                       v
+---------------------------------------------------------------------+
|                     BackupReplicationService                        |
| - Server-Side Encryption (SSE-S3 AES256 / SSE-KMS)                  |
| - Zero PHI/PII Metadata Tagging                                     |
| - Credential Scrubbing & Secret Sanitization                        |
+---------------------------------------------------------------------+
                                                       |
                                            TLS 1.3 Upload Stream
                                                       |
                                                       v
+---------------------------------------------------------------------+
|                  Off-Site S3-Compatible Storage                     |
| - Object Lock / WORM Retention Policy                               |
| - AWS S3 / MinIO / Cloudflare R2 / GCS                              |
+---------------------------------------------------------------------+
                                                       |
                                        Remote Integrity Verification
                                                       |
                                                       v
+---------------------------------------------------------------------+
|                 Disposable Database Restore Check                   |
| - Download artifact & verify SHA-256                                |
| - Restore to roadsos_remote_restore_tmp                            |
| - Validate Alembic revision & table row counts                     |
+---------------------------------------------------------------------+
```

---

## 2. Environment Configuration

All configuration is provided exclusively via environment variables. Credentials are never hardcoded.

| Variable | Description | Default | Required in Production |
| :--- | :--- | :--- | :--- |
| `BACKUP_REPLICATION_ENABLED` | Enables/disables off-site replication (`true`/`false`) | `false` | Yes (`true`) |
| `BACKUP_STORAGE_BUCKET` | Target S3-compatible bucket name | `""` | Yes when enabled |
| `BACKUP_STORAGE_PREFIX` | Key prefix inside the target bucket | `roadsos/backups/` | No |
| `BACKUP_STORAGE_REGION` | Storage region | `us-east-1` | No |
| `BACKUP_STORAGE_ENDPOINT` | Custom endpoint URL (e.g. MinIO `http://localhost:9000`) | `None` (AWS default) | Optional |
| `BACKUP_STORAGE_ACCESS_KEY` | S3 API Access Key ID | `None` | Yes (if no IAM role) |
| `BACKUP_STORAGE_SECRET_KEY` | S3 API Secret Access Key | `None` | Yes (if no IAM role) |
| `BACKUP_STORAGE_KMS_KEY_ID` | Optional AWS KMS Key ARN / ID for SSE-KMS encryption | `None` | Optional |

---

## 3. Encryption & Secret Redaction

* **At Rest Encryption**:
  - By default, uploads enforce Server-Side Encryption with S3-managed keys (`ServerSideEncryption="AES256"`).
  - If `BACKUP_STORAGE_KMS_KEY_ID` is set, uploads enforce AWS KMS encryption (`ServerSideEncryption="aws:kms"`, `SSEKMSKeyId=...`).
* **In Transit Encryption**: All network connections enforce TLS 1.2+ / TLS 1.3 HTTPS streams.
* **Secret Redaction**: All logging and error tracebacks pass through `sanitize_secret_string()`. Access keys, secret keys, passwords, and authorization tokens are automatically replaced with `[REDACTED_ACCESS_KEY]`, `[REDACTED_SECRET]`, or `[REDACTED_DB_PASS]`.

---

## 4. Object Immutability & Protection Policy (WORM)

To prevent accidental deletion, ransomware tampering, or unauthorized modification of off-site backups:
* **Object Lock / WORM**: Buckets must be provisioned with S3 Object Lock enabled in **Compliance Mode** for a retention period of 30 days.
* **Restricted Delete Permissions**: Application IAM credentials are granted `s3:PutObject`, `s3:GetObject`, and `s3:ListBucket` permissions only. `s3:DeleteObject` and `s3:DeleteObjectVersion` are explicitly denied to application service roles.
* **Bucket Versioning**: Enabled to preserve previous object versions if overwritten.

---

## 5. Object Metadata Schema

Every replicated backup artifact carries S3 user metadata. Metadata is sanitized and contains **zero PHI/PII**:

```json
{
  "backup_filename": "roadsos_backup_roadsos_db_20260910_120000.sql.gz",
  "creation_timestamp": "2026-09-10T12:00:00+00:00",
  "sha256_checksum": "8d474bf3c35e2d482f640dc8c6a48ffc7ac98d5898a760d2429fc7041253fe37",
  "app_version": "step19",
  "alembic_revision": "a1b2c3d4e5f6",
  "postgresql_version": "15.4",
  "backup_size": "28359",
  "replication_timestamp": "2026-09-10T12:00:05+00:00"
}
```

---

## 6. Remote Integrity & Download Verification

Verification is performed programmatically via `backend/scripts/verify_remote_backup.py`:
1. Locates target remote key.
2. Streams object and calculates local SHA-256 digest.
3. Compares against object metadata `sha256_checksum` and uploaded `.sha256` manifest file.
4. Verifies Gzip compression structure (`gzip.GzipFile` header read check).
5. Returns `status: completed` or fails loudly if checksum mismatch occurs.

---

## 7. Restore from Remote Off-Site Backup Workflow

Automated testing restores remote artifacts into an isolated disposable database:

```text
Remote Object Storage
         |
  download_file()
         |
  SHA-256 Integrity Verification
         |
  Restore into temporary DB: roadsos_remote_restore_tmp
         |
  Validate Alembic revision: a1b2c3d4e5f6
         |
  Validate Table Row Counts (users, triage_jobs, triage_events, etc.)
         |
  Drop roadsos_remote_restore_tmp cleanly
```

---

## 8. Retention Lifecycle & Execution Order

Local and off-site backup management follows a strict lifecycle:

1. **Create**: Local `pg_dump` snapshot generated.
2. **Validate**: Local SHA-256 digest computed and manifest written.
3. **Replicate**: Uploaded to S3 storage with SSE encryption and metadata.
4. **Verify Remote Integrity**: `head_object()` SHA-256 and size verified.
5. **Mark Replicated**: Local marker file `roadsos_backup_*.sql.gz.replicated` written.
6. **Eligible for Cleanup**: GFS retention policy (`cleanup_backups.py`) can delete local file when expired. Un-replicated backups are retained even if past cutoff age.

---

## 9. Prometheus Disaster Recovery Replication Metrics

Exposed at `GET /metrics`:

| Metric Name | Type | Description |
| :--- | :--- | :--- |
| `disaster_recovery_replication_last_success` | Gauge | `1` = last replication succeeded, `0` = failed |
| `disaster_recovery_replication_last_duration_seconds` | Gauge | Duration of last off-site replication in seconds |
| `disaster_recovery_replication_last_backup_size_bytes` | Gauge | File size of last replicated backup artifact |
| `disaster_recovery_replication_latest_backup_age_seconds` | Gauge | Age of latest off-site replicated backup artifact |
| `disaster_recovery_replication_failures_total` | Counter | Total count of off-site replication failures |

---

## 10. Prometheus Alert Definitions

```yaml
groups:
  - name: roadsos_offsite_disaster_recovery.rules
    rules:
      - alert: RoadSOSBackupReplicationFailed
        expr: disaster_recovery_replication_last_success == 0
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "RoadSOS Off-Site Backup Replication Failed"
          description: "The latest off-site backup replication attempt failed. Inspect worker logs for storage network or credential issues."

      - alert: RoadSOSBackupReplicationStale
        expr: disaster_recovery_replication_latest_backup_age_seconds > 90000
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "RoadSOS Off-Site Replicated Backup Stale"
          description: "The latest off-site replicated backup is older than 25 hours. Verify automated snapshot cron job."

      - alert: RoadSOSRemoteBackupIntegrityFailure
        expr: increase(disaster_recovery_replication_failures_total[1h]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "RoadSOS Remote Backup Integrity Mismatch"
          description: "SHA-256 verification failed during remote backup verification."

      - alert: RoadSOSRemoteBackupMissing
        expr: disaster_recovery_replication_latest_backup_age_seconds == -1
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "RoadSOS Remote Backup Missing"
          description: "No off-site replicated backup marker found."
```

---

## 11. Emergency Off-Site Disaster Recovery Runbook

### Scenario: Primary PostgreSQL Host Destroyed & Local Backup Storage Lost

1. **Provision Fresh Target Host & PostgreSQL 15 Instance**:
   ```bash
   docker run -d --name production-db-recovery -e POSTGRES_PASSWORD=roadsos_password -e POSTGRES_DB=roadsos_db -p 5432:5432 postgres:15
   ```

2. **Retrieve Off-Site Backup Key**:
   List available backup objects in S3 bucket:
   ```bash
   aws s3 ls s3://roadsos-production-backups/roadsos/backups/
   ```

3. **Download & Verify Remote Backup**:
   Run `verify_remote_backup.py` to stream latest backup and verify SHA-256:
   ```bash
   python backend/scripts/verify_remote_backup.py --key roadsos/backups/roadsos_backup_roadsos_db_latest.sql.gz --outdir /tmp/disaster_recovery
   ```

4. **Restore Database**:
   Import SQL archive into target PostgreSQL instance:
   ```bash
   gunzip -c /tmp/disaster_recovery/roadsos_backup_roadsos_db_latest.sql.gz | psql -h localhost -U roadsos -d roadsos_db
   ```

5. **Verify Alembic Revision & Schema Integrity**:
   ```bash
   alembic stamp head
   alembic check
   ```

6. **Start Application & Workers**:
   ```bash
   docker-compose up -d backend worker
   ```
