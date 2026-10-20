# ADR-0056: Require explicit simulator verification profiles

## Status

Accepted.

## Context

The legacy simulator profiles omitted verification settings. `evaluate_verification_mechanism` silently supplied imaging rates, symptom and marker thresholds, visibility burden, and deterministic imaging-result behavior as Python literals. This made the default profile's outcome-generation contract invisible in its versioned data and left unregistered assumptions in executable code.

## Decision

- Every simulator population profile must declare a verification object with provenance, imaging trigger parameters, visibility threshold, and an explicit result model.
- `deterministic_visible_recurrence` preserves the legacy profiles' prior rule: an imaged visible latent recurrence is positive, all other imaging results are negative, and no additional result draw consumes random state.
- `imperfect_test_characteristics` uses profile-declared sensitivity and specificity.
- Legacy profile values are migrated from the former source defaults and remain explicitly uncalibrated synthetic assumptions. No biological, clinical-policy, or model-performance claim follows.
- Missing or malformed verification settings fail during profile validation. Frozen result artifacts remain unchanged.

## Consequences

Verification parameters and result semantics are reviewable with the selected profile. Seeded legacy cohort fingerprints are tested to prove this migration preserved output behavior. Future verification changes require a versioned profile and registered sensitivity analysis; they must not be tuned against frozen model-evaluation cohorts.
