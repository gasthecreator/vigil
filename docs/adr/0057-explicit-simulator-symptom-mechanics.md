# ADR-0057: Configure simulator symptom mechanics explicitly

## Status

Accepted.

## Context

The simulator generated symptom grades from source-literal burden thresholds, grade scales, and caps. Legacy and K3 profiles also relied on code-default baseline symptom probabilities. These values affect verification triggers and model-visible features but were not fully declared in each versioned population profile.

## Decision

- Every population profile must declare baseline symptom probabilities and a complete rule for each tracked symptom.
- Each rule names its latent trigger and grade states, thresholds, grade offset, and scale; the profile also declares maximum and baseline grades and provenance.
- The values migrated from source are synthetic assumptions, not clinically calibrated symptom likelihoods or severity mappings.
- Invalid or incomplete symptom contracts fail during profile validation. Legacy seeded cohort fingerprints must remain unchanged during this metadata/configuration migration.

## Consequences

Symptom generation is reviewable and reproducible from the selected profile. Future symptom-model changes require a new versioned configuration and sensitivity analysis before model-selection use. Existing result artifacts remain untouched.
