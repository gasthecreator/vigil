# ADR-0058: Configure facility laboratory effects explicitly

## Status

Accepted.

## Context

Legacy and v1 profiles relied on source literals for facility count, per-patient laboratory offset spread, and analyzer scale range. Newer profiles sampled shared effects per facility, but the assignment mode was described in prose rather than represented as a validated setting. These choices affect feature distributions and study transport stress.

## Decision

- Every population profile declares facility count, offset spread, scale range, assignment mode, and a human-readable assignment description.
- `per_patient` preserves the legacy independent patient/analyte effect behavior; `shared_by_facility` uses one seeded effect per facility and analyte.
- Legacy values are migrated from source defaults to the v0/v1 JSON profiles. Seeded fingerprint tests must verify no output changes.
- These are synthetic measurement-system assumptions, not estimates of real inter-laboratory variation.

## Consequences

Facility effect assignment is visible and validated at profile construction. A future change to distribution or assignment requires a versioned profile and sensitivity analysis. Frozen study artifacts remain untouched.
