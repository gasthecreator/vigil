# Tier 2b report: K5 laboratory harmonisation (and retraction of the old S5)

> Status: SUBMITTED FOR REVIEW. Verdict, maturity and every overseer column are untouched. Maturity stays L0. `DRAFT-UNREVIEWED`. Synthetic data only.

## Outcome in one paragraph
K5 was rebuilt as a tested estimator and evaluated once, as pre-registered, on 100 frozen replications. **The pre-registered criterion H3 failed and the kill rule fired: K5 is not claimed to help.** An older mean-shrinkage method did better than K5 in the primary simulated cell and worse in the case-mix scenario. The change detector could not be calibrated to its target on streams that contain disease progression. All of it is in `experiments/EXP-K5-001/CONCLUSION.md`, with every number copied from the script-written `results.json` and `REPORT.md`.

## What was built
| Item | Where |
|---|---|
| Evidence for the laboratory spread (E23, audited excerpt) | `docs/EVIDENCE.md`, `docs/evidence/excerpts/E23_jia_2026_ca153_eqa.md` |
| Pre-registration, committed alone before any code or run | `experiments/EXP-K5-001/PREREG.md` (commit `c7a4ba8`) |
| Estimator (REML, closed-form posterior, safetensors and ONNX export, CUSUM helper) | `packages/vigil-ml/vigil_ml/k5.py` |
| Multi-laboratory simulator layer | `packages/vigil-sim/vigil_sim/multilab.py` |
| Runner (writes every number), frozen results and report, development results | `experiments/EXP-K5-001/run.py`, `results.json`, `REPORT.md`, `dev_results.json`, `dev_results_v1_pre_amendment2.json` |
| Tests (invariants of PREREG section 8, simulator layer, runner, retraction, registry) | `packages/vigil-ml/tests/test_k5.py`, `test_k5_experiment_runner.py`, `packages/vigil-sim/tests/test_multilab.py` |
| Model registry (no metric values; parity tests and result hash) | `scripts/build_model_registry.py`, `packages/vigil-ml/vigil_ml/registry/model_registry.json` |
| Retraction of the old S5 | `reports/ml/RETRACTED/S5_HARMONISATION_V1/`, `reports/ml/RETRACTED/README.md` |
| ADR, model card, stub, hand-over | `docs/adr/0024-k5-replaced-and-not-claimed.md`, `docs/model_cards/MODEL-CARD-K5.md` (and the duplicate under `docs/models/`), `docs/STUBS.md` S-009, `docs/HANDOVER.md` H-113 |

## Findings and deviations (all of them)
1. **Old S5 was a constant.** `run_study_s5` subtracted the injected offset by hand and returned the literal 34.2; its model card repeated it. Retracted; the old method's `run_study_s5` now raises. I also edited `reports/ml/BENCHMARK_REPORT.md` and `reports/ml/results.json` by removing the S5 entry (text and key removal, not a re-run of the whole benchmark runner, to avoid unrelated cross-platform numeric drift). This is an edit of two result-bearing files that I did not produce by script; the other studies' numbers are untouched.
2. **PREREG amendments (2).** Amendment 1 before any run (the specified new-site evaluation cohort could not show an effect). Amendment 2 after the first development run, before the frozen run: reporting additions only. No hypothesis, grid, rule or threshold was changed. Full list in `CONCLUSION.md`.
3. **The first development run revealed a runner defect (the calibration returned the last grid value without saying the target was missed).** Fixed by recording `target_attained`; the first development file is kept unchanged.
4. **One of my tests had wrong arithmetic** (null-alarm bound). Corrected before the frozen run.
5. **H1 is not met in the sourced cell**; H4 and H5 and H3 are not met; H2 is met. The strongest baseline (legacy mean shrinkage) is reported first. K5 is not claimed to help.
6. **The cause of the interval under-coverage is a hypothesis** (model misfit with the simulator's disease dynamics) supported by the control scenario; it is not isolated by an experiment.
7. **Frozen run time** 905 s on four worker processes (value from `REPORT.md`).

## Files changed outside this tier's scope
`scripts/run_benchmarks.py`, `scripts/verify_phase.py` (S5 references only), `reports/ml/BENCHMARK_REPORT.md`, `reports/ml/results.json` (S5 entry removed), `packages/vigil-ml/vigil_ml/harmonisation_k5.py` (legacy notice; method raises), ledger row T2b (my own). `tests/acceptance_*`: untouched.
