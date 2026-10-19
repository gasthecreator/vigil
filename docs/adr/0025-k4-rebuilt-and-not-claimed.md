# ADR 0025: K4 is rebuilt as six tested families, the old stub and its S4 and S9 usage are retired, and K4 is not claimed to help

## Status
Accepted as an engineering decision. `DRAFT-UNREVIEWED` clinically (nothing here is a clinical claim).

## Context
The earlier K4 (`vigil_ml/deep_zoo_k4.py`) never trained: `DeepZooK4.fit` set a flag, `predict_risk` was a hand-written logistic formula, and study S4 returned literal dictionaries. Study S9 of `scripts/run_benchmarks.py` still scored that formula under the name `K4_DeepZoo`, and the K4 model card quoted the retracted S4 numbers.

## Decision
1. **Build K4 for real** (`vigil_ml/k4.py`): six forward-only families (GRU-D, GRU-ODE-Bayes encoder, Neural CDE, continuous-time transformer, GRUwE, selective state-space model) behind one interface and one training loop, masked-analyte pre-training, safetensors and ONNX export (no pickle), tests for causality, padding invariance, mask semantics, planted-signal learning and shuffled-label failure, pre-training loss reduction, export parity, determinism and the absence of simulator-internal reads (`packages/vigil-ml/tests/test_k4.py`).
2. **Pre-register and run** `experiments/EXP-K4-001/` (PREREG committed alone; development replications for two selections; one frozen run). Four amendments were made before the frozen run, each with evidence from development data (`PREREG.md`); the most consequential are A3c (a one-sided canary) and A4 (symptom inputs, because the classical baselines have them).
3. **Accept the result.** H1 not met (pre-training lowered AUC), H2 not met (no deep family beat the strongest baseline), H3 "scale does not help"; all three kill rules fired. K4 is not claimed to help; no pre-trained checkpoint is exported or registered; `model_registry.json` carries K4 as "claim not earned" at L0.
4. **Retire the old stub**: `deep_zoo_k4.py` deleted, its imports and tests removed, the `K4_DeepZoo` row removed from `scripts/run_benchmarks.py`, `reports/ml/S9_CROSS_GENERATOR/{results.json,REPORT.md}` and `reports/ml/results.json` by deleting the key and the row, with a disclosure appended to the S9 report. The model card is rewritten without the retracted numbers.

## Alternatives considered
- Keep the stub and fix its study: rejected; the stub is not a model.
- Tune until H1 or H2 passes: rejected; the grid and the single frozen run were fixed in the PREREG.
- Re-run `scripts/run_benchmarks.py` to regenerate S9 without the row: rejected, to avoid unrelated cross-platform numeric drift in rows that did not change.
- Keep the canary rule exactly as first written: it would have voided the study on a statistic (a permuted-label network averages 0.448) that cannot indicate leakage; the amendment is disclosed first in `CONCLUSION.md` and the original-rule outcome is stated there.

## Consequences
- STUBS S-004 now states K4's status exactly; a new stub S-016 records that `ProductionEnsembleK8` is a hand-written formula whose "k4_deep_zoo" term is not K4 (it was unlisted).
- The model-card, benchmark and registry surfaces contain no K4 number that is not in `experiments/EXP-K4-001/results.json`.
- Not decided here: whether pre-training on real longitudinal laboratory data (human action H-114), a forecasting objective, or more labelled data would change the result. Each needs its own pre-registration.
