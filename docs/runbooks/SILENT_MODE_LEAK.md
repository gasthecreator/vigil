# Runbook: Silent-mode leak

**Alert:** Clinician-facing route returned or stored a model output while `VIGIL_SILENT_MODE=true`, or shadow URL equals clinical DB.  
**Related:** [`../clinical/SILENT-MODE.md`](../clinical/SILENT-MODE.md), ADR-0022, SLO “Silent-mode leak”.

## Immediate
1. Set traffic to fail closed: keep `VIGIL_SILENT_MODE=true`; do **not** disable silent mode to “fix” a leak.
2. Capture the offending `request_id`, route, and response body (redact PHI).

## Diagnose
1. Confirm `VIGIL_SILENT_SHADOW_DATABASE_URL` ≠ `DATABASE_URL` (startup must refuse otherwise).
2. Reproduce with the security / silent-mode suite (`apps/api/tests/test_silent_mode.py`).
3. Check whether a new route was added without a `ROUTE_POLICY` `silent=` annotation.

## Recover
1. Patch the route to `diverts` / `blocked` per policy; add a regression test.
2. Purge leaked rows from the **clinical** DB only with an audited maintenance script; never copy shadow → clinical to “reconcile”.
3. Notify the clinical lead if any real partner data was exposed (H- entries in `HANDOVER.md`).

## Verify
Unauthenticated and clinician clients receive withheld/blocked behaviour; shadow store still receives predictions.
