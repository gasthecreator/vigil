---
status: accepted
date: 2026-10-20
decision-makers: Q-7 executor
consulted: Overseer review pending
informed: Contributors
---

# 0054. Quarantine facility-derived M10 signal statistics

## Context

The facility audit endpoint passed all observations for a patient into one numeric series, without preserving analyte identity. It then applied a single hard-coded CV pair to M3 and described the result as a surveillance signal meeting clinical review criteria. The M10 implementation also depends on K2's claimed anytime-valid guarantee, which Q-6 has retracted pending a valid replacement. M3's separate simulator evaluation did not discriminate gradual recurrence (manifest-rise AUROC 0.4961; all-post AUROC 0.4910). These assumptions cannot support facility-level missed-signal statistics.

## Decision

Keep M10's explicitly labelled synthetic benchmark available for research. When the facility API finds an active-consented observation within the requested lookback window, return HTTP 503 with `m10_facility_analysis_unavailable`; do not run M3/K2 or emit facility counts. An empty eligible cohort may still return an empty, non-synthetic report. The endpoint's check uses stored consent and observation timestamps and does not construct synthetic placeholder trajectories.

## Consequences

The UI's current synthetic benchmark path is unchanged. Facility-derived M10 statistics remain unavailable until an amended preregistration defines analyte-specific inputs and laboratory variation, valid detection methods and thresholds, a patient-level estimand, and external validation. The historical M10-V2 synthetic artifacts remain unchanged and cannot be presented as facility validation. Overseer acceptance tests remain unchanged.
