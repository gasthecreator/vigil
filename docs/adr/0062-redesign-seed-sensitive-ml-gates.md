# ADR-0062: Replace seed-sensitive ML thresholds with valid software contracts

- Status: Accepted
- Date: 2026-10-20
- Decision owner: repository owner (explicit approval in the PR #79 repair thread)

## Context

PR #79 has four failing checks whose assertions mix software correctness with
single-cohort performance: fixed AUC floors for B1/B4/fast landmark logistic,
an event-only row permutation for a fitted fast landmark model, a single-seed
G1 conditional lead-time SD ceiling, and a 40-simulation K1 coverage cutoff.
The existing proposals identify these as invalid or seed-sensitive test
contracts. No failing score, seed, generator parameter, or acceptance threshold
will be used to tune a model or simulator.

## Decision

- Baseline tests assert finite, bounded prediction scores and defined metric
  values. Comparative AUC and model selection remain study outcomes under
  patient-disjoint, censor-aware preregistrations; the generic unit suite does
  not assert a fixed performance ranking.
- The fast landmark research baseline retains its latent-column/input canary.
  Its row-wise event-only permutation is removed because it does not preserve a
  patient-level survival outcome. A patient-grouped K3 statistical null test is
  deferred until the genuine K3 model and its estimand are implemented and
  preregistered. The current class is not thereby validated as K3.
- The G1 unit test keeps numeric-contract checks for conditional lead-time SD.
  It makes no calibration claim. Calibration requires a new multi-seed,
  mask-aware registered study with uncertainty and coverage reporting.
- K1's 40 simulation coverage check uses a two-sided exact 95% binomial
  interval and requires nominal 90% coverage to lie within it. The check no
  longer treats an unattainable `[0.75, 0.97]` cutoff on increments of 0.025 as
  a calibration criterion. It remains algorithmic synthetic evidence only.

## Consequences and limits

These changes repair software gates; they do not establish predictive
performance, synthetic calibration, K3 validity, or clinical validity. The
associated studies remain required by the core ML repair plan. Historical
results remain untouched and are not reinterpreted. CI may run the frozen K1
simulation fixture to verify the revised generic criterion, but no parameter,
seed, or implementation is tuned to that fixture.

## Evidence

The implementation and verification commit for this decision will be recorded
in `docs/PROGRESS.md`. The linked proposals remain the detailed problem and
evidence records: `PROP-CORE-ML-CENSOR-AWARE-GATE.md`,
`PROP-K3-SHUFFLED-OUTCOME-CANARY.md`,
`PROP-CORE-ML-MEASURED-CALIBRATION-GATE.md`, and
`PROP-K1-ACCEPTANCE-BOUNDARIES.md`.
