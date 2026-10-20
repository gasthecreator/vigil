# EXP-M12-001 provenance and data-contract audit

Status: **historical, provenance-incomplete, and not current model-selection evidence**.

## Evidence inspected

- The preregistration is identified by the Tier 2 report as commit `62d84b3`.
- The runner and M12 implementation are present in commit `a190366be21db4a311f49b4683322bad66016b9e`.
- Commit `e7494d34eac2fd12cfc1a6aab5f2c0b87ea625ff` added `results.json`, `dev_results.json`, and `REPORT.md`; its parent is `a190366be21db4a311f49b4683322bad66016b9e`.
- `results.json` itself contains no analysis `code_sha`; the parent relation makes `a190366` a plausible source state, not verified run provenance.
- The canonical append-only log `data/audit/frozen_test_access.jsonl` contains no EXP-M12-001 access entry. The legacy `reports/ml/frozen_test_access_log.jsonl` entry for `SYNTHETIC-MULTISITE-CONSORTIUM-S10` refers to the old S10 access from `scripts/run_benchmarks.py`, not this experiment.
- The committed runner has no frozen-access logging or clean-tree/source-SHA guard. The output commit identifies a plausible committed source state, but does not prove the working tree or exact time at test access. No access record is being backfilled from inference.
- The frozen run predates ADR-0039's corrected early-censor label semantics. The current extractor emits an unknown (`NaN`) binary label when loss to follow-up occurs before the horizon. M12's runner passes those labels to `train_sgd` / `train_dp_sgd` without filtering or censor-aware training weights, and its scorer previously returned fabricated `0.5/0/0/0` metrics for empty cohorts while accepting unknown calibration labels.

## Repair and disposition

Current M12 training functions now reject empty, non-finite, non-binary, or shape-inconsistent training inputs; federated training rejects empty or invalid sites. The EXP-M12-001 score path now rejects empty cohorts, invalid probabilities, misaligned arrays, and unknown calibration labels. Regression tests cover these fail-closed cases.

These guards do not repair or validate the frozen results. Preserve the generated outputs unchanged and treat the claimed H1–H4 outcomes as historical observations only, not evidence for selecting a model, validating a censor-aware objective, or establishing privacy. A replacement experiment requires a new preregistration, new seeds, canonical access logging before test generation, a training objective that handles censoring, calibration metrics appropriate to censored outcomes, and an accountant whose sampling assumptions match the implemented DP mechanism.

The pre-registration, original output files, old S10 retraction, and prior conclusions remain preserved. This audit supplements them; it does not rewrite their history or claim real-world privacy, clinical performance, or utility.
