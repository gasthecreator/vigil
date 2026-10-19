# Retraction: legacy S3 verification-bias study

**Status: RETRACTED as evidence for verification-bias correction, estimator ranking, or product evaluation.** The historical `PREREG.md`, `results.json`, and `REPORT.md` remain preserved and must be read with this notice.

The legacy run does not meet its own preregistration or current ML data contract:

- It used lifetime `true_recurrence_event` rather than a horizon-specific event with censoring and competing-event semantics.
- It set every unverified outcome to negative (`y_obs = 0`) before complete-case, IPW, and latent-class estimation.
- The reported `score` is a hand-set sigmoid of maximum CA 15-3 with literal center, scale, and 0.50 threshold; it is not a fitted or validated diagnostic model.
- Verification was reduced to whether imaging ever occurred, without using the recorded per-exam result or modeling its sensitivity/specificity.
- The preregistration specifies ten replications; the runner generated one cohort with seed 101.
- The generated report asserts IPW as the default evaluation method. That decision is unsupported; verification adjustment requires a valid observed-data model and correctly scoped estimand.

`scripts/run_benchmarks.py::run_study_s3` now fails closed. The aggregate runner is retired because it also emits stale S1/S9/K3 claims. Do not use any S3 number as evidence. A future verification-bias method must be separately specified and preregistered against the corrected data contract.
