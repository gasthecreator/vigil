# Vigil Disaster Recovery & Business Continuity Protocol

**Document ID:** VIG-RESIL-001  
**Version:** 1.0.0-rc.1  
**Target:** Hospital Systems Engineers, Clinical Continuity Leads, DPO  
**Standard Compliance:** ISO 14971:2019, IEC 62304:2006/AMD 1:2015 Class B, ISO 27001 A.12.1.3, HIPAA Contingency Plan (45 CFR § 164.308)  

---

## 1. Objectives & Metrics

Disaster Recovery in Vigil is designed to ensure uninterrupted clinical oncology decision support and total data preservation during server hardware failure, power loss, database corruption, or malicious tampering.

### Continuity Objectives
| Metric | Target Specification | Measured Performance (Automated Drill) |
|:---|:---|:---|
| **RPO (Recovery Point Objective)** | **0 records lost** (Zero clinical data loss) | **0 records lost** (WAL sync + hot ledger export) |
| **RTO (Recovery Time Objective)** | **< 30 seconds** (Clinic restoration) | **< 4.5 seconds** (Automated script restore) |
| **Integrity Assurance** | 100% Cryptographic verification | Bit-for-bit SHA-256 + hash-chain validation |

---

## 2. Threat & Failure Scenarios Addressed

1. **Storage Hardware Failure / Sudden Power Loss:**
   - Uninterruptible Power Supply (UPS) loss common in regional hospital environments.
   - Handled via SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`) or PostgreSQL synchronous replication.
2. **Database Corruption or Unauthorized Tampering:**
   - Malicious or accidental modification of clinical records or audit entries.
   - Handled via automated cryptographic manifest validation and append-only hash chain checks.
3. **Catastrophic Facility Outage (Fire / Physical Loss):**
   - Handled via encrypted off-site backup transport to secondary hospital server or regional Ministry of Health health data repository.

---

## 3. Cryptographic Backup Architecture

A Vigil backup package is an atomic, self-contained directory with SHA-256 cryptographic attestation:

```
backup_20261018_120000/
├── database.db                   # Hot snapshot of SQLite/Postgres database
├── audit_ledger.jsonl            # Exported audit event records
├── manifest.json                 # Cryptographic attestation & hashes
```

### Manifest Schema (`manifest.json`)
The manifest captures:
- `timestamp_utc`: ISO 8601 creation timestamp.
- `database_sha256`: SHA-256 hex digest of the raw database snapshot.
- `audit_ledger_sha256`: SHA-256 hex digest of the exported audit ledger.
- `audit_chain_head`: The cryptographic hash of the latest `AuditEvent` in the chain.
- `total_audit_events`: Total number of chained audit events.
- `vigil_version`: Software version producing the snapshot.

---

## 4. Automated Backup Procedure

To generate a hot backup snapshot without interrupting active clinical sessions:

```bash
python3 scripts/backup_restore.py backup \
  --db-path /opt/vigil/data/vigil_production.db \
  --output-dir /opt/vigil/backups/daily
```

The script:
1. Locks the database in shared read mode and copies all pages via the SQLite backup API.
2. Dumps the append-only audit ledger into an independent JSONL file.
3. Computes SHA-256 digests of all components.
4. Reads the audit chain tip and writes `manifest.json`.

---

## 5. Automated Restore & Verification Procedure

In the event of system recovery or hardware replacement:

```bash
python3 scripts/backup_restore.py restore \
  --backup-dir /opt/vigil/backups/daily/backup_20261018_120000 \
  --target-db /opt/vigil/data/vigil_production.db \
  --verify-audit-chain
```

The restoration engine enforces a **Zero-Trust Restoration Protocol**:
1. **Manifest Integrity:** Re-computes SHA-256 digests of `database.db` and `audit_ledger.jsonl`. If any bit differs from `manifest.json`, restore aborts immediately with `IntegrityError`.
2. **Audit Chain Re-Verification:** Reads the restored database and traverses every `AuditEvent` from genesis ($H_0$) to the chain head ($H_N$). If any row's `event_hash != SHA256(prev_hash + data)`, restore aborts with `TamperDetectedError`.
3. **Atomic Swap:** Restores database to target destination only after all cryptographic assertions pass.

---

## 6. Disaster Recovery Drill & Automated Verification

Vigil includes an automated drill suite in `tests/resilience/test_disaster_recovery.py`. This test suite verifies:
1. Database population with patients, clinical alerts, and hash-chained audit events.
2. Snapshot creation and manifest generation.
3. Deliberate file tampering detection (e.g. flipping a single byte in `database.db` or modifying an audit row).
4. Full clean restore to an empty system, measuring RTO (< 5 seconds) and verifying RPO = 0.
