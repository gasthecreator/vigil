# ADR-0059: Configure baseline analyte sampling explicitly

## Status

Accepted.

## Context

The simulator capped between-patient analyte variation and clipped generated baseline values to source-literal fractions of the registry reference interval. These choices shape every model input but were absent from the versioned population profiles.

## Decision

- Every population profile declares the between-patient CV cap, lower and upper reference fractions, and provenance for baseline analyte sampling.
- The legacy values are migrated as synthetic assumptions; their presence in a profile is not evidence of clinical calibration.
- Missing or malformed settings fail during profile validation.
- Legacy seeded cohort fingerprints remain the compatibility criterion; do not regenerate or rewrite historical result artifacts.

## Consequences

Baseline analyte generation is reviewable alongside the profile and analyte registry. Changing these values alters model inputs and requires a new profile plus preregistered sensitivity analysis before any model-selection use.
