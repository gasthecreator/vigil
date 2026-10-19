# Proposal: revise two K1 acceptance boundaries

## Problem

The frozen K1 acceptance suite produced two failures on source commit `bbc1eded06ee9445e8a49c2a0e30324d46b45f42`. The tests remain unchanged.

1. `test_route_recovers_truth_with_posterior_intervals[amortized]` observes 39/40 covered truth values, or 0.975, for the nominal 90% interval. The test's maximum is 0.97, so one additional covered case changes a pass into a failure. With 40 simulations, coverage changes only in increments of 0.025; the current upper bound falls between attainable outcomes.
2. `test_training_is_real` expects `shuffle_pairs=True` to act as a negative control that breaks the observation/parameter association. The current option permutes both arrays together, which preserves every pair and correctly still learns. The test's intent is sound, but the option's implementation and naming do not identify that negative-control behavior.

The K1-WORLD recurrence gate xfailed under its registered stub. No acceptance assertion was edited or used for tuning.

## Proposed change

- Replace the raw 40-case interval-coverage cutoff with a registered finite-sample criterion, such as a binomial confidence interval around nominal coverage or a larger independently seeded simulation count.
- Make the training negative control explicit and separately named. It should deliberately break observation/parameter pairing only in the negative-control path, while the production training path always preserves pairs. Keep the acceptance test's real-fit and seed reproducibility checks.

## Evidence and boundary

The one-time command and complete output are recorded in `experiments/EXP-K1-004/ACCEPTANCE.md`. Results are also recorded in `experiments/EXP-K1-004/results.json`. These failures are not used to tune the estimator. Any implementation change after the frozen-cohort access requires a new experiment ID and new product-transfer seeds; the fixed acceptance seed has already been consumed and must not be used for development.

## Decision needed

Overseer review should decide the finite-sample recovery criterion and whether to revise the test helper API or its negative-control setup. Until then, the K1 acceptance gate is NOT MET and this branch is not ready to merge.
