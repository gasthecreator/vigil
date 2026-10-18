# Tier 2d report: K6 active sensing (and retraction of the old S6)

> Status: SUBMITTED FOR REVIEW. Verdict, maturity and every overseer column are untouched. Maturity stays L0. `DRAFT-UNREVIEWED`. Synthetic data only.

## Outcome in one paragraph
K6 was rebuilt as a tested planner and evaluated once, as pre-registered, on 20 frozen replications (frozen run 2, after a defective panel table in run 1). **H1 and H2 met in this simulator: at equal assumed cost the K6 frontier is 2.3 days earlier than the fixed-schedule frontier and 0.8 days earlier than the risk-triggered frontier.** H3 (25 percent cost saving at the delay of the 3-month schedule) was **not met**. The pre-registered fallback when H1 and H2 both hold is still: **a suggestion with reasons shown, and only a simulation claim; no clinical benefit is claimed.** The 2.3-day margin sits on a ~60-day symptomatic-presentation effect; the P1-only ablation matches the free-panel K6; on generator G3 the risk-triggered frontier is earlier. ESMO guidance (E25) does not recommend routine markers in asymptomatic patients. All of it is in `experiments/EXP-K6-001/CONCLUSION.md`, with every number copied from the script-written `results.json` and `REPORT.md`.

## What was built
| Item | Where |
|---|---|
| Evidence for the named schedules and the marker counter-indication (E25, audited excerpt) | `docs/EVIDENCE.md`, `docs/evidence/excerpts/E25_park_2024_esmo_followup.md` |
| Pre-registration, committed alone before any K6 code or run | `experiments/EXP-K6-001/PREREG.md` (commit `9e1fe8b`) |
| Planner, hazard, policies; dense-world engine | `packages/vigil-ml/vigil_ml/k6.py`, `k6_engine.py`, `packages/vigil-sim/vigil_sim/surveillance.py` |
| Runner (writes every number), frozen run 2, development files, superseded run 1 | `experiments/EXP-K6-001/run.py`, `results.json`, `REPORT.md`, `dev_results.json`, `dev_results_grid1.json`, `run1_superseded/` |
| Tests (invariants of PREREG section 8 and amendment 1, panel-table counting, retirement of the old stub, runner smoke) | `packages/vigil-ml/tests/test_k6.py`, `test_k6_experiment_runner.py` |
| Reproducibility check in CI (code hash, aggregate re-derivation, report re-render, fixed and heuristic arms of replication 0) | `scripts/verify_study_reproducibility.py` (`verify_k6_study`) |
| Model registry entry (simulation claim only; no metric values) | `scripts/build_model_registry.py`, `packages/vigil-ml/vigil_ml/registry/model_registry.json` |
| Retraction of the old S6 | `reports/ml/RETRACTED/S6_ACTIVE_SENSING/` (banners), `reports/ml/RETRACTED/README.md` |
| ADR, model card, stub, hand-over | `docs/adr/0026-k6-rebuilt-simulation-claim-only.md`, `docs/models/MODEL-CARD-K6.md`, `docs/STUBS.md` S-005, `docs/HANDOVER.md` H-115 |

## Findings and deviations (all of them)
1. **Old S6 was a literal dictionary.** Visit counts, dollar costs and delays were typed in; the report printed "CONFIRMED". Retracted; `run_study_s6` now raises. I edited `reports/ml/BENCHMARK_REPORT.md` (the retracted-studies sentence only; no re-run of the benchmark runner).
2. **PREREG amendments (4).** A1 and A2 before any run (planner objective was wrong by construction; bootstrap/canary coverage rules). A3 after development replications: `w` grid extended downwards, the one change section 7 permits when the frontier does not reach the budgets. A4 after frozen run 1: panel table counted only visits that had already missed detection (`s_π = 0`, floored to 0.02). I had read run 1's verdicts before finding that defect. Run 1 is kept in `run1_superseded/` and is not the decision. The amendment-4 identity check held: every fixed, heuristic and risk-triggered record is bit-identical to run 1; only sensitivity and the K6/canary arms changed.
3. **H1 and H2 met as written** (no minimum effect size). The observed margins are 2.3 and 0.8 days. At B26, K6 versus risk-triggered includes 0. H3 not met. Strongest baseline reported first. "Infeasible" is not written.
4. **What drives the margin.** `k6_P1` matches `k6_free`; tumour markers did not help under alert rule A (symptom grade ≥ 2 already gives panel-table sensitivity 1.000). `k6_prior` is near zero. Scenario A is dominated by symptomatic presentation (~60 days). On G3, S2 changes sign.
5. **Not built, as declared:** nested-Monte-Carlo expected information gain on K1; reinforcement learning.
6. **Commit hygiene slip.** Frozen run 1 and the K6 verifier were one commit (`ab9a869`). History not rewritten. Run 2 results are a results-only commit (`1bec6f4`).
7. **Cross-platform reproducibility.** CI re-derives the aggregate, the report, and the fixed/heuristic arms of replication 0. Hazard-model arms are not compared bit-for-bit across machines (`VIGIL_VERIFY_K6_FULL=1` is opt-in).

## Files changed outside this tier's scope
`scripts/run_benchmarks.py` and `scripts/verify_phase.py` (S6 references), `reports/ml/BENCHMARK_REPORT.md` (sentence only), `packages/vigil-ml/vigil_ml/__init__.py` and `tests/test_phase3_models.py` (removed old K6 imports and tests), `docs/README.md`, `CHANGELOG.md`, ledger row T2d (my own). `tests/acceptance_*`: untouched.
