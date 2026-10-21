# ADR-0047: Add explicit G1 clearance and G2 shot-noise mechanisms

## Status

Accepted for a new synthetic simulator profile, pending EXP-CORE-ML-011 validation. This ADR approves no model-performance result or clinical calibration claim.

## Context

Q-7 package B found that legacy G1 directly mapped saturating burden to marker increments without clearance, while legacy G2 used a fixed small burst count and a recent-burst window. Those implementations did not meet the named continuous secretion/clearance and stochastic shot-noise mechanisms expected of the core simulator. Replacing equations in existing profiles would silently invalidate historical runs and artifacts.

## Decision

- Preserve legacy and core-v3 profile behavior for historical reproduction.
- Add `balanced_synthetic_core_v4` with explicit synthetic G1 first-order secretion/clearance parameters and G2 homogeneous Poisson event, amplitude, and clearance parameters.
- Propagate G1 state on a fixed configured time grid and G2 events on independent patient-scoped time/amplitude streams. Measurement visits sample those states and do not define the integration or event process.
- Keep the new parameters explicitly uncalibrated. V4 is unavailable as evidence of clinical biology or model performance until registered mechanism validation, sensitivity studies, and separate calibration work support stronger claims.
- Register and execute EXP-CORE-ML-011 once; preserve all legacy outputs unchanged. Model comparisons using v4 require separate preregistration and fresh cohorts.

## Consequences

The code now distinguishes legacy stress mechanisms from the new mathematical forms, and the dataset card describes their limits. Existing calibration tests on legacy profiles remain unchanged; their known G1 standard-deviation gate failure is not tuned away. EXP-CORE-ML-011 can reject the implementation, in which case the failure remains recorded and its seeds are not reused.
