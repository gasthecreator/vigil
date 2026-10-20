# ADR-0060: Make simulator mechanics and cohort schedules explicit

## Status

Accepted.

## Context

G1/G2/G3 dynamics, assay missingness, visit scheduling, and cohort-generation defaults were partly embedded in source and silently substituted when profile values were absent. This made profile review incomplete and allowed an accidental source edit to change generated model inputs without an explicit profile change.

## Decision

- Every supported population profile declares generator mechanics, missingness behavior, and cohort scheduling assumptions, including the historical legacy values.
- Generator code reads those values directly. Optional algorithm modes (G1 marker kinetics and G2 shot noise) are represented explicitly as configured null values when disabled.
- Cohort size, duration, visit interval, follow-up taper, and UTC date origin are profile-controlled defaults; explicit call arguments continue to override size, duration, and nominal interval.
- Exact seeded cohort fingerprints across G1/G2/G3 and legacy, v1, and K3 profiles guard compatibility. This verifies implementation parity only, not scientific validity.
- Changes to these values remain synthetic assumptions; any use for model selection requires preregistration and sensitivity analysis.

## Consequences

Profiles are larger but disclose the inputs shaping generated features and labels. Missing or malformed required settings fail during construction or call validation. Historical frozen results remain untouched; fingerprints do not validate calibration or clinical performance.
