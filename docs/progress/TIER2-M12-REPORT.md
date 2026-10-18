# Tier 2e report: M12 federated averaging and DP-SGD (replacement for retracted S10)

> Status: SUBMITTED FOR REVIEW. Verdict, maturity and every overseer column are untouched. Maturity stays L0. `DRAFT-UNREVIEWED`. Synthetic data only.

## Outcome in one paragraph
M12 was built as in-process FedAvg with pairwise secure aggregation and DP-SGD, and evaluated once as pre-registered on 10 frozen replications. **H3 (the 3 pp kill versus centralised training) was met; H2 (FedAvg without DP) was not; B4 remains stronger than every MLP arm; headline ε̂ ≈ 46 at δ = 1/910 is a loose bound.** The kill rule did not fire. The module is not wired, is not a pilot, and is not a legal privacy claim. Numbers live in `experiments/EXP-M12-001/CONCLUSION.md`, copied from the script-written `results.json` and `REPORT.md`. The old S10 renderer no longer prints CONFIRMED.

## What was built
| Item | Where |
|---|---|
| Evidence for FedAvg and DP-SGD (E26, E27, audited excerpts) | `docs/EVIDENCE.md`, `docs/evidence/excerpts/E26_mcmahan_2017_fedavg.md`, `E27_abadi_2016_dp_sgd.md` |
| Pre-registration, committed alone before any code or run | `experiments/EXP-M12-001/PREREG.md` (commit `62d84b3`) |
| FedAvg, masks, DP-SGD, moments accountant | `packages/vigil-ml/vigil_ml/m12.py` (commit `96610c7`) |
| Invariant tests (PREREG section 8) | `packages/vigil-ml/tests/test_m12.py` |
| Runner, development file, frozen results and report | `experiments/EXP-M12-001/run.py`, `dev_results.json`, `results.json`, `REPORT.md` |
| ADR, model card, stub, hand-over | `docs/adr/0027-m12-simulation-only-not-wired.md`, `docs/model_cards/MODEL-CARD-M12.md`, `docs/STUBS.md` S-006, `docs/HANDOVER.md` H-116 |

## Findings and deviations (all of them)
1. **Old S10 was literals.** `render_s10_markdown` printed H1–H3 CONFIRMED from a dictionary. Retracted path already under `reports/ml/RETRACTED/`; the functions now raise and point at this experiment.
2. **No PREREG amendments.** Development (3 replications, 10 s) was not used to change any registered knob. Frozen run once (33 s).
3. **H3 met because D's mean pooled AUC exceeded C's**, on a design that gives F/D 20×2 local epochs and C 4 epochs. H2 still failed. B4 0.8277 vs D 0.7108. Reported in `CONCLUSION.md`; not used to retrain C.
4. **E26 has no Crossref DOI** (PMLR 54). The arXiv `10.48550/` identifier 404s on Crossref; the entry uses the PMLR URL and the arXiv abs URL. E27's ACM DOI resolves.
5. **Flower and Opacus were not added**, as registered.
6. **Canary mean 0.5237**, VOID false. Accountant on the E27 example: ε = 1.259 in [1.15, 1.40].

## Files changed outside this item's scope
`scripts/run_benchmarks.py` (S10 functions raise), `scripts/verify_phase.py` (S10 paths → EXP-M12-001), `scripts/verify_study_reproducibility.py`, `scripts/build_model_registry.py`, `reports/ml/RETRACTED/README.md` (S10 row points here), ledger row T2e (my own). `tests/acceptance_*`: untouched.
