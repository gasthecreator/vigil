# Operational Runbook: Backup & Disaster Recovery

**Classification:** Standard Operating Procedure (SOP)  
**Governing Standard:** `docs/MASTER_PLAN.md` §9.4 Observability and Operations  
**Audience:** Site Reliability Engineers, Clinical System Administrators  

---

## 1. Objectives & SLO Targets

- **Recovery Point Objective (RPO):** $\le 15$ minutes maximum data loss tolerance. In local SQLite single-node deployments, file-level streaming / copy on write provides RPO $\le 1$ minute.
- **Recovery Time Objective (RTO):** $\le 5$ minutes to complete full cold restoration and resume surveillance services.
- **Integrity Target:** 100% cryptographic audit chain continuity verified via `verify_audit_chain` against external WORM / off-host anchor.

---

## 2. Backup Procedures

### 2.1 Artifacts to Back Up
1. **Platform Relational Database:**
   - Production PostgreSQL: `pg_dump -Fc vigil > /backup/vigil_$(date +%s).dump`
   - Local/Edge SQLite: atomic snapshot via `.backup` or filesystem copy when no active write transaction is open:
     ```bash
     sqlite3 vigil_prod.db ".backup '/backup/vigil_backup.db'"
     ```
2. **External Cryptographic Audit Anchor:**
   - Location specified by `VIGIL_AUDIT_ANCHOR_PATH` (e.g., `/var/log/vigil/audit_anchor.jsonl` or remote WORM bucket `s3://...` / `gs://...`).
   - Append-only file holding periodic head-hash commitments.
3. **Field Encryption Keys:**
   - `FIELD_ENCRYPTION_KEYS` managed through external secrets manager (Vault / AWS Secrets Manager / GCP Secret Manager).

### 2.2 Backup Verification & Manifest Generation
After every backup snapshot:
```bash
sha256sum /backup/vigil_backup.db > /backup/manifest.sha256
sha256sum /backup/audit_anchor.jsonl >> /backup/manifest.sha256
```

---

## 3. Disaster Recovery (Restore) Procedure

### Step 1: Quarantine Affected Services
Stop the API service and background workers to prevent split-brain writes:
```bash
systemctl stop vigil-api vigil-worker
```

### Step 2: Restore Database and External Anchor
Copy verified backup snapshot and anchor files to target storage locations:
```bash
cp /backup/vigil_backup.db /data/vigil_prod.db
cp /backup/audit_anchor.jsonl /var/log/vigil/audit_anchor.jsonl
```

### Step 3: Verify Checksums
```bash
sha256sum -c /backup/manifest.sha256
```

### Step 4: Cryptographic Audit Traversal & Verification
Before opening the API to traffic, run the audit verification routine:
```bash
uv run python -c "from vigil_api.audit import verify_audit_chain; res = verify_audit_chain('/data/vigil_prod.db', '/var/log/vigil/audit_anchor.jsonl'); assert res['valid'], f'Integrity failure: {res}'; print('Audit chain verified successfully.')"
```

### Step 5: Resume Surveillance Services
```bash
systemctl start vigil-api vigil-worker
curl -f http://localhost:8000/
```

---

## 4. Automated Drill Protocol
Execute the automated drill suite periodically:
```bash
uv run python scripts/backup_restore_drill.py
```
Output results are logged to `reports/operations/backup_restore_drill.json`.
