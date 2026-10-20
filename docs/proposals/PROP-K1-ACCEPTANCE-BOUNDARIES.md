# Proposal: revise two K1 acceptance boundaries

## Problem

The frozen K1 acceptance suite produced two failures on source commit `bbc1eded06ee9445e8a49c2a0e30324d46b45f42`. The tests remain unchanged. A later source audit confirmed one failure was an implementation defect and fixed it on the Q-7 branch.

1. `test_route_recovers_truth_with_posterior_intervals[amortized]` observes 39/40 covered truth values, or 0.975, for the nominal 90% interval. The test's maximum is 0.97, so one additional covered case changes a pass into a failure. With 40 simulations, coverage changes only in increments of 0.025; the current upper bound falls between attainable outcomes.
2. `test_training_is_real` expects `shuffle_pairs=True` to act as a negative control that breaks the observation/parameter association. The implementation permuted both arrays together, preserving every pair. Q-7 now permutes the parameter targets relative to the observations only in the explicitly requested negative-control path; ordinary training continues to preserve each simulated pair. The unchanged test passes after this correction.

The K1-WORLD recurrence gate xfailed under its registered stub. No acceptance assertion was edited or used for tuning.

## Proposed change

- Keep the training negative-control implementation correction; it is covered by the unchanged acceptance test and does not alter ordinary training.
- Replace the raw 40-case interval-coverage cutoff only through overseer disposition and a registered finite-sample criterion, such as a binomial confidence interval around nominal coverage or a larger independently seeded simulation count. Do not adjust the interval scale against the consumed fixed seed.

## Evidence and boundary

The original one-time command and complete output are recorded in `experiments/EXP-K1-004/ACCEPTANCE.md`. Results are also recorded in `experiments/EXP-K1-004/results.json`. The unchanged K1 v2 acceptance file now reports 3 passed and 1 expected xfail after the negative-control correction. The amortized coverage boundary remains unresolved at 39/40 (0.975) against the 0.97 ceiling. This test remains a consumed fixed-seed check and is not tuning evidence.

On PR #79 head `ac53e66`, GitHub acceptance CI reports the amortized 90% interval coverage as `0.97` outside `[0.75, 0.97]`. The displayed value is rounded to two decimals; the earlier local 39/40 result is 0.975 and exceeds the upper bound. The frozen assertion remains unchanged.

The latest PR #79 CI run (`39417463523`, backend-acceptance job `118609860472`, merged test commit `9bce4ff14d7da866635543010bb1411b32bb5082`) reproduces the same failure: one acceptance test fails with displayed coverage `0.97` outside `[0.75, 0.97]`; the other K1 checks pass or are the registered expected failure. No threshold or seed was changed.

The next PR #79 run on branch head `38339ace662c186db6c20b5081c938f0c3f28d89` (CI run `39432790607`, backend-acceptance job `118662192993`; Postgres run `39432790682`, job `118662076287`) reproduces the same `39/40 = 0.975` result. The Postgres job completed its migration, security and deployment steps successfully; only the acceptance suite failed on this K1 boundary. No implementation, seed, or assertion change was made for this result.

## Decision needed

Overseer review is needed only for the finite-sample coverage criterion. The negative-control defect is fixed in implementation; the K1 acceptance gate remains NOT MET while the unchanged coverage check is unresolved, so this branch is not ready to merge.
