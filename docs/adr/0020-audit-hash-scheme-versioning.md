# ADR 0020: Versioned audit-hash scheme and compatibility with chains and backups written by earlier code

## Status
Accepted (closes overseer condition P15-G, `docs/progress/VERDICT-P8B.md` defect 8).

## Context
Phase 8b changed `calculate_audit_hash` so that a timestamp passed as a *string* is parsed and re-rendered in UTC ISO form instead of being used verbatim (`str(timestamp)`). No ADR or compatibility test accompanied that change. The question: do chains and backups written before that change still verify?

Facts established from git history (`git show 9709295:apps/api/vigil_api/models/v2.py`, the last commit before the change):
- For a `datetime` input (the only input `record_audit_event` ever passes in production) the old and the new code produce byte-identical canonical input (`timestamp.astimezone(UTC).isoformat()`; naive values taken as UTC). **Existing production chains are unaffected.**
- For a `str` input the old code hashed the string verbatim. Strings only occur in the restore tooling (`scripts/backup_restore.py` reads SQLite text columns). The old code therefore could not verify a datetime-hashed chain from raw SQLite strings at all; the 8b change made that path work. Rows whose digest was computed *from* a raw string (synthetic or test-created chains) were verifiable only by the old behaviour.

## Decision
1. **Two named schemes.** `v1-canonical-utc` (all new rows): canonical JSON, timestamp rendered by `canonical_audit_timestamp()` (datetime or any parseable ISO/SQLite string → UTC `isoformat()`). `v0-raw-timestamp-string` (read-only legacy): the digest the pre-8b code computed from a string timestamp used verbatim.
2. **Writers only ever produce v1** (`calculate_audit_hash` is v1).
3. **Verifiers accept the digest of either scheme** via `audit_hash_candidates()`: v1 always, v0 only when the stored timestamp is a string. `verify_audit_chain` reports `hash_schemes` (counts per scheme) so an operator can see whether legacy rows exist; `scripts/backup_restore.py` verification uses the same function.
4. **Why accepting two encodings is safe:** both are deterministic functions of the same fields (previous hash, actor, role, action, resource, details, instant). Any change to any field, or to the instant by one microsecond, changes both digests; an attacker gains nothing from the second encoding unless they can already compute SHA-256 chains, in which case v1 alone would not help either (tail deletion is covered by the external anchor, ADR on audit anchors, P7-D).
5. **No schema change and no stored version column:** the scheme is identified per row by which candidate matches. A future scheme (v2) must be added to `audit_hash_candidates()` with a golden fixture before it can be written.

## Evidence (tests that fail if this is wrong)
`tests/resilience/test_audit_hash_compat.py`, golden data from `scripts/generate_audit_compat_fixture.py`, which **executes the old function extracted verbatim from git history (`9709295`)**:
- new `calculate_audit_hash` equals the old digest for 12 rows written from aware, non-UTC-offset and naive datetime inputs and for their SQLite/JSONL string forms;
- the production verifier (`verify_audit_chain`) accepts the old 12-row chain and reports `{"v1-canonical-utc": 12}`;
- 8 rows hashed from raw strings by the old code verify only as v0, and their v1 digest differs (so the v0 path is genuinely exercised);
- a one-field edit or a 1 µs timestamp edit of an old chain is detected;
- restore of an old-format backup package (manifest in the rc.1 format) succeeds for both chain kinds; an attacker who edits the database **and** recomputes the manifest checksums is stopped by chain verification (`TamperDetectedError`).
While writing the restore test a real defect surfaced and was fixed: `restore_backup` failed when the target directory did not exist (restore onto a fresh host).

## Known limitation
The ORM verifier (`verify_audit_chain`) receives `datetime` objects from SQLAlchemy and therefore verifies only v1 digests; rows hashed by the old code from raw strings verify in the restore tooling (string path) but not through the ORM verifier. No production code path ever wrote such rows.
