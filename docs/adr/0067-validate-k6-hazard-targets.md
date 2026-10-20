# ADR-0067: Validate K6 hazard training inputs before conversion

- Status: Accepted
- Date: 2026-10-20

## Context

`HazardModel.fit` converted its target matrix to integers before validation. Fractional labels could therefore be silently truncated, while non-finite labels could reach model and calibration code after an implementation-dependent cast. The registered K6 target is a patient-grouped binary detectable-event indicator at each fixed horizon; it is not an arbitrary numeric score.

## Decision

Validate that feature selections are non-empty, unique integer indices (not booleans or silently truncated floats); validate that the feature matrix is 2D with in-range selected columns, permit missing (`NaN`) feature values for XGBoost, and reject infinities. Require one finite binary target per row and registered horizon, and aligned one-dimensional patient groups with at least two distinct identifiers before splitting or fitting.

## Consequences

Malformed targets and split inputs fail before fitting. The module now passes strict mypy, and the repository's configured typing gate includes `k6.py` so this contract remains checked in CI. This does not alter the K6 estimand, repair the model's scientific assumptions, or validate the preserved EXP-K6-001 results. No study cohorts or result artifacts were regenerated.
