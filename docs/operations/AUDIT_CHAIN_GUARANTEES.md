# Cryptographic Audit Chain: Security & Integrity Guarantees

**Document Version:** 1.0  
**Phase:** 5b  
**Scope:** Vigil Platform Cryptographic Audit Subsystem (`vigil_api/audit.py`, `vigil_api/models/v2.py`)  
**Compliance Context:** HIPAA Security Rule §164.312(b), FDA AI/ML Software as a Medical Device (SaMD) Traceability, ISO 27001 A.12.4  

---

## 1. Subsystem Architecture

Every clinical mutation and clinical data read within Vigil produces an immutable record in the `audit_events` relational table. The table is structured as an append-only forward-linked cryptographic hash chain:

$$\text{curr\_hash}_i = \text{SHA-256}\Big(\text{prev\_hash}_{i-1} \parallel \text{timestamp}_i \parallel \text{actor\_id}_i \parallel \text{actor\_role}_i \parallel \text{action}_i \parallel \text{resource\_type}_i \parallel \text{resource\_id}_i \parallel \text{canonical\_json}(\text{details}_i)\Big)$$

Where:
- The genesis event $i=0$ anchors to the fixed 64-hex-character zero string (`"0" * 64`).
- Details are canonicalized into sorted, compact JSON without whitespace.
- Periodic external state anchors (`audit_anchors`) snapshot the pair `(head_hash, total_events)`.

---

## 2. What the Audit Chain GUARANTEES

### 2.1 Tamper Evident Forward-Integrity
- **Retroactive Field Modification Detection:** If an adversary or compromised application process alters any field in historical event $k$ (e.g., changes an actor ID, overwrites an alert action from `"escalate"` to `"explained"`, or alters an analyte concentration), $\text{curr\_hash}_k$ ceases to match the payload.
- **Cascade Breakage:** Because $\text{curr\_hash}_k$ serves as $\text{prev\_hash}_{k+1}$, all subsequent hash links $k+1, k+2, \dots, N$ fail validation.
- **Verification Guarantee:** `verify_audit_chain(db)` mathematically verifies the complete sequential chain in $O(N)$ time and Pinpoints the exact index where tampering occurred.

### 2.2 Tail-Deletion and Truncation Detection
- In standard chained ledgers without external anchors, an attacker with write access can silently delete the trailing $M$ rows from the table, leaving the remaining prefix $1 \dots N-M$ valid.
- Vigil enforces **External Head Anchoring** (`AuditAnchor`):
  Whenever the verification suite or checkpoint worker runs, it compares the current `head_hash` and row count against the latest anchored state. If total rows in `audit_events` is less than `anchor.total_events`, or if the anchor's recorded hash is absent from the chain, `verify_audit_chain` raises an immediate integrity violation (`"Tail deletion detected"`).

### 2.3 Row-Level Immutability Invariant
- The database schema and API ORM explicitly forbid `UPDATE` or `DELETE` operations on `AuditEvent`. All endpoints only invoke `record_audit_event()`, enforcing append-only semantics.

### 2.4 Complete Auditing of Clinical Lifecycle Events
- **Patient Creation:** `patient.created`
- **Consent Lifecycle:** `consent.granted`, `consent.revoked`
- **Clinical Reads:** `patient.read`, `observations.read`, `fhir.observation.read`
- **Observation Ingestion:** `observation.ingest` (recording analyte, raw/canonical values, M3 action, alert state)
- **Alert Actions:** `alert.acknowledged` (recording disposition and clinician notes)
- **Follow-up Tasks:** `follow_up.transition` (recording status transitions and reason)
- **Reminders:** `reminder.dispatched` (recording channel, receipt ID, escalation level)

---

## 3. What the Audit Chain DOES NOT Guarantee

Understanding the physical boundaries of the cryptographic design is vital for hospital IT risk assessments:

### 3.1 Direct DBA / Storage-Layer Rewrite with Recomputed Hashes
- **Limitation:** If a rogue database administrator (or attacker with root SQL access) possesses write access to both `audit_events` and the local `audit_anchors` table, they could rewrite history and recompute all sequential SHA-256 hashes from the point of edit forward.
- **Mitigation:** Production deployments must mirror `AuditAnchor` records to a WORM (Write Once Read Many) cloud bucket (e.g., Google Cloud Storage with Object Retention / Bucket Lock or AWS S3 Glacier Vault) or an append-only distributed ledger.

### 3.2 Non-Repudiation Without Client-Side Asymmetric Keys
- **Limitation:** Vigil generates hashes server-side using application credentials. While the actor ID and role are cryptographically bound into the event hash, the actor did not sign the payload with an individual private hardware key (e.g., smart card or FIDO2 token).
- **Mitigation:** Legally binding non-repudiation requires mutual TLS (mTLS) with client certificates or external PKI document signing integrated with the hospital EHR.

### 3.3 Raw Out-of-Band Physical Database Corruption
- **Limitation:** Bit rot, underlying disk sector failure, or ungraceful database termination will cause chain verification to fail identically to malicious tampering. The chain detects divergence but cannot distinguish malicious tampering from disk corruption.
- **Mitigation:** Standard RAID/ZFS filesystem integrity checking and point-in-time database WAL replication.

### 3.4 Unmonitored Out-of-Band Reads
- **Limitation:** If an engineer executes direct SQL queries (`SELECT * FROM observations;`) directly in SQLite or PostgreSQL using the CLI, that access is not routed through FastAPI and therefore does not generate an `observations.read` audit row.
- **Mitigation:** Database access must be restricted to the application service account; administrative access must require audited bastion proxying (e.g., Teleport / Cloud SQL IAM).

---

## 4. Operational Verification Commands

To verify chain integrity programmatically or as part of automated infrastructure health checks:

```python
from vigil_api.audit import verify_audit_chain
from vigil_api.database import SessionLocal

db = SessionLocal()
try:
    result = verify_audit_chain(db)
    print(
        f"Audit chain verified: {result['total_events']} events, head hash: {result['head_hash']}"
    )
finally:
    db.close()
```

If the return dictionary has `"valid": True`, the entire historical log is cryptographically intact and corresponds to the anchor.
