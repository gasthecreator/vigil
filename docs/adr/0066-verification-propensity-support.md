# ADR-0066: Match verification IPW support checks to the estimand

- Status: Accepted
- Date: 2026-10-20

## Context

`evaluate_ipw_verification` weights verified observations by the inverse of `P(V=1 | X)`. It previously rejected probability 1 for every row whenever verification varied. This incorrectly made a valid case—an observed verified patient whose verification probability is 1—undefined. Positivity for missing-outcome IPW requires the observation/verification probability to be positive across the target population; it does not require it to be less than 1 ([Molina, Sued, and Valdora, 2017](https://arxiv.org/abs/1704.01978), §2).

## Decision

Permit propensity 1 for verified rows. Continue to mark the estimate undefined if any target row has zero verification probability. Also reject an unverified row assigned propensity 1 because that assignment is incompatible with the observed verification mask. Do not clip or truncate weights; expose the existing maximum-weight and effective-sample-size diagnostics instead.

## Consequences

The evaluator no longer discards an identifiable finite-sample case solely because some observed rows are always verified. The estimator still relies on conditional exchangeability, positivity, and a sufficiently specified propensity model. This code change is not validation of those assumptions or a clinical estimate.
