# ADR-0039: Landmark features respect observation time and outcome contracts

- **Status:** Proposed
- **Date:** 2026-10-19
- **Decision owners:** Q-7 executor, subject to overseer review

## Context

The feature named `*_slope_90d` admitted observations up to 120 days old. Acceleration used raw value differences, so the same constant-rate trajectory produced different acceleration values under irregular visit spacing. Zero-mean CV was reported as a measured zero, and zero follow-up after a landmark was changed to one day. The cohort builder also defaulted missing outcome metadata to “no recurrence”, silently skipped observations whose patient row was absent, and accepted duplicate same-day observations despite lacking a within-day order.

## Decision

- The 90-day slope uses only observations within the named 90-day window.
- Acceleration is the second time-normalized divided difference and is unavailable when its denominator is not defined.
- A zero-mean CV is missing/unavailable, not a measured zero.
- True zero follow-up remains zero.
- Horizon labels require explicit observed-recurrence metadata; missing/invalid outcomes, duplicate patient rows, unknown patient references, duplicate patient/day rows, post-administrative-follow-up observations, and mismatched event/type dates fail closed. Configured event times beyond administrative follow-up remain censored rather than becoming observed events; the simulator's bounded post-diagnosis transition observations are excluded from predictive landmarks.
- The module-level labeled feature builder no longer manufactures an outcome-free patient table.

## Consequences and limits

This changes generated feature values and may change all downstream model results. Existing frozen study outputs are not edited or reused as evidence for the corrected features. A new preregistered synthetic comparison must precede any result-producing rerun. No real clinical validity follows from the unit tests.

## Verification

- `packages/vigil-ml/tests/test_features.py` covers the 90-day window, irregular-time acceleration, ambiguous same-day visits, missing outcome metadata, invalid event/follow-up boundaries, non-finite times, missing current measurements, and zero follow-up semantics.
- Latest focused verification: feature + metric + leakage + simulator generator/surveillance suites, 57 passed. Ruff and `git diff --check` passed.
- The fixed baseline AUC assertions in `packages/vigil-ml/tests/test_baselines_sanity.py` remain unchanged. The focused run reports 28 passes and the same two comparative gate failures; proposal `PROP-CORE-ML-CENSOR-AWARE-GATE.md` records the unresolved issue. Do not tune these features to the fixed test cohort.
