# K1 acceptance gate record

Acceptance tests ran once with `VIGIL_ACCEPTANCE=1 VIGIL_CONTRACT_V2=1` at candidate source commit `bbc1eded06ee9445e8a49c2a0e30324d46b45f42`. The overseer-authored tests under `tests/acceptance_k1/` were not modified.

**Result:** 14 passed, 1 xfailed, 2 failed.

- The K1-WORLD recurrence gate xfailed because S-001 registers the simulator/event-semantics mismatch. The xfail is not evidence that K1 predicts recurrence.
- `test_route_recovers_truth_with_posterior_intervals[amortized]` measured 39/40 coverage (0.975), above the test's upper bound of 0.97.
- `test_training_is_real` found that `shuffle_pairs=True` still learned because the current implementation permutes observations and their targets together. This is a negative-control semantic mismatch; the production training call uses `shuffle_pairs=False`.

These results were not used to tune the implementation. The full failure traces were observed in the one-time test run; see `docs/proposals/PROP-K1-ACCEPTANCE-BOUNDARIES.md` for the evidence-based proposal. Do not rerun this fixed acceptance cohort as development data.
