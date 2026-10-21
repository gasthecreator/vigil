---
status: accepted
date: 2026-10-20
decision-makers: Q-7 executor
consulted: Overseer review pending
informed: Contributors
---

# 0053. Synthetic provenance is explicit and source-bound

## Context

Patient creation previously defaulted records to synthetic, while several routes also hard-coded `synthetic=true`. That label controlled whether unvalidated M3/K2 outputs were visible, so a caller-supplied provenance claim could change the serving path.

## Decision

Patient records created through the patient API default to non-synthetic unless the request explicitly identifies generated/test data. Only the local environment may create those records with `synthetic=true`. The audited patient-creation, M3/K2, symptom, caregiver-share and disclosure routes carry the stored patient provenance rather than inferring it from a response default.

## Consequences

Ordinary enrollment and records with missing provenance fail closed to non-synthetic serving. The M3/K2 visible scoring path remains limited to local synthetic records; non-synthetic records abstain until clinical validation is available. Historical rows retain their stored provenance. Other routes that still hard-code synthetic status are tracked for the remaining Q-7 serving-path audit; this ADR does not claim those routes are repaired.
