---
id: PROP-0002
title: K2 detector state grows without bound (per-update cost O(observations per patient))
author: Executor (final-build Tier 0)
date: 2026-10-18
status: DRAFT
plan_version_impact: NONE
---

# PROP-0002: K2 detector state grows without bound

## 1. Problem Statement
`vigil_ml.k2.SequentialDetector.update` appends every observation to `history` and recomputes `np.mean(self.history)` over all of it (`packages/vigil-ml/vigil_ml/k2.py`, `update`). The API persists the whole detector in `patients.detector_state` as JSON (`apps/api/vigil_api/ml/detector_helpers.py`: `history`, `days`), rewritten on every observation. Per-update CPU and the size of the row therefore grow linearly with the number of observations of that patient.

## 2. Evidence Base
Soak run 1 (`reports/load/SOAK_TEST_HTTP_RESULTS_run1_10patients.json`, written by `scripts/run_soak_test.py`): 10 patients, 1807 s, 28,678 requests, p95 first quarter 1412.7 ms and last quarter 9983.72 ms (the file's own verdict: FAIL). A cProfile of lab POSTs (terminal output, not committed) showed JSON encoding (`json.encoder.iterencode`) and row loading growing with history. This is partly an artefact of the harness concentrating all writes on 10 patients (about 2000 observations each), which is why the canonical soak uses 200 patients; it is not an artefact of the code path, which has no bound.

## 3. Proposed Change
Keep the detector's mathematics identical but store sufficient statistics instead of the raw series: running count and sum (so the baseline mean is `sum / n`), the last value(s) the detector actually uses, and the e-process components. Keep `history`/`days` readable on load for existing rows (migration on first write). Parity test: for random series, the new implementation's `log_e`, `alert` and components equal the current implementation's to 1e-12.

## 4. Considered Alternatives
- **Cap `history` at a window.** Pros: trivial. Cons: changes the statistic (baseline becomes a moving average), which invalidates the K2 evaluation in `reports/ml/` and needs a new study.
- **Leave as is.** Pros: no K2 change. Cons: cost grows for long-lived patients; unbounded JSON column.

## 5. Evaluation & Verification Criteria
Parity test above; the K2 acceptance suites (`tests/acceptance_k1`, `tests/acceptance_3b`) unchanged and green; the load/soak harnesses show per-update cost independent of history length.

## 6. Kill / Rollback Criterion
Any parity failure > 1e-9 on the property test, or any change in a K2 benchmark number.

## 7. Impact on Master Plan
None. `vigil-ml` is a shared package: this needs an ADR and a downstream re-run before it is implemented, so it is filed here and not applied by the executor.
