# EXP-K5-001 provenance and replay-safety audit

Status: **synthetic-only historical evidence; no clinical validation**.

The committed `dev_results.json`, earlier development snapshot, `results.json`, and `REPORT.md` must remain unchanged. The persistent `--dev` and `--frozen` paths previously overwrote these outputs; they now fail before detector calibration when the target files already exist. Regression tests verify that all affected bytes remain unchanged.

The prior `--smoke` path supplied a literal detector record with `target_attained=True`, so it did not exercise the detector-calibration code. Smoke now runs the real calibration on 150-patient synthetic train/evaluation cohorts, then runs its tiny study replications on a separate, explicit smoke seed range. Both ranges are disjoint from development, calibration, and frozen seeds. Smoke writes no artifacts. The focused runner tests exercise this path and verify the seed separation.

No frozen or development cohorts were generated and no stored outputs were changed during this audit. These changes improve replay safety and smoke-path coverage only; the historical result remains bound to its original implementation and the limitations in `CONCLUSION.md`.
