---
status: accepted
date: 2026-10-20
decision-makers: Q-7 executor
consulted: Overseer review pending
informed: Contributors
---

# 0055. Label M3/M5 worked journeys as synthetic illustrations

## Context

The M3/M5 generator used hard-coded marker values and CV assumptions, then labelled its synthetic cases “Analytical Error,” “Benign Fluctuation,” and “True Recurrence.” Those labels state scenario truth, but M3 returns conditional component weights and actions under unvalidated assumptions. M5's verifier establishes only that text follows structured facts. The generated report and M5 card therefore overstated what either module had established.

## Decision

Keep the deterministic examples as synthetic renderer illustrations. Rename titles and contexts to describe generated values and M3 model outputs, and state that scenario labels are not ground truth. Describe M5 verification as a fact-to-text check, not model or clinical validation. Preserve old phase reports as historical records and add a Q-7 correction note; do not change model results or acceptance contracts.

## Consequences

M3/M5 examples remain useful for deterministic renderer behavior, but cannot support claims about recurrence detection, benignity, analytical error, calibration, or clinical utility. Any future performance claim requires a separately preregistered evaluation with independent labels and a validated estimand.
