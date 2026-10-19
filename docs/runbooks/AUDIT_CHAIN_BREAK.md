# Runbook: Audit chain break

**Alert:** `verify_audit_chain` fails, or hash mismatch vs external anchor.  
**Related:** [`../operations/AUDIT_CHAIN_GUARANTEES.md`](../operations/AUDIT_CHAIN_GUARANTEES.md), SLO “Audit chain unbroken”.

## Immediate
1. Freeze writes that append audit events if safe (maintenance window / silent mode for new model outputs).
2. Capture the failing head hash, expected anchor hash, and clock skew.

## Diagnose
1. Diff the last N audit rows against the previous known-good backup.
2. Check for clock rollback, restored DB without matching anchor, or dual-writer corruption.
3. Confirm field-encryption key rotation did not rewrite historical ciphertext unexpectedly.

## Recover
1. Prefer **restore to last verified backup + anchor pair** over “repairing” hashes in place.
2. If only the anchor is missing, restore the anchor file from WORM/off-host storage; do not invent anchors.
3. Document the gap: any unverifiable window is a safety incident, not a silent fix.

## Verify
Re-run the chain verifier; attach stdout to the incident record.
