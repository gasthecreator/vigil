---
status: accepted
date: 2026-10-20
decision-makers: Codex (Executor)
consulted: None
informed: Contributors
---

# 0051. Quarantine unsupported M1 organ priors

## Context

The M1 implementation returned hand-authored subtype proportions, undocumented age and stage pseudocount changes, normal-approximation intervals labelled as credible intervals, and confidence based on the cited study's total cohort size. Its two cards described materially different estimates and behavior. E12 is classified `SECONDARY`; its denominators and subtype-specific estimates are not reconciled to M1's intended estimand. The API had already been quarantined under ADR-0041, but the package class remained public and callable, and M4 converted its outputs into priors.

## Decision

Keep the legacy M1 class and conversion function importable for compatibility, but make all prediction and M4 conversion entrypoints fail closed. Withdraw both historical cards and replace the E12 dossier's unsupported product-use claims with the current evidence status. Do not change historical result artifacts or acceptance tests. Track M1 as unavailable until an evidence-backed estimand, estimates, uncertainty method, and independent validation are established.

## Consequences

Package callers can no longer obtain unsupported M1 probabilities through direct or M4-mediated inference. The API and package behavior agree. This is containment, not a replacement model or evidence that M1 performs well; prior outputs remain historical and unusable for patient inference or model selection.
