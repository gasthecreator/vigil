# ADR 0024: K5 is rebuilt as a tested estimator, the old S5 is retracted, and K5 is not claimed to help

## Status
Accepted as an engineering decision. `DRAFT-UNREVIEWED` clinically (nothing here is a clinical claim).

## Context
The earlier K5 (`vigil_ml/harmonisation_k5.py`) and its study S5 were found, while preparing Tier 2, to be self-fulfilling: the "harmonised" arm subtracted the injected offset by hand (`harm_obs = raw_obs - 5.5`), the new-site Brier reduction was the literal `34.2`, and the model card repeated both. Its estimator also shrinks a laboratory's mean value, which reflects case mix as well as laboratory bias.

## Decision
1. **Retract old S5** to `reports/ml/RETRACTED/S5_HARMONISATION_V1/` (banner added, `RETRACTED/README.md` row added), remove it from `scripts/run_benchmarks.py`, `scripts/verify_phase.py`, the benchmark report and `reports/ml/results.json`; `HierarchicalLabHarmoniserK5.run_study_s5` now raises.
2. **Build K5 as an estimator** (`vigil_ml/k5.py`): a log-scale mixed model with a patient fixed intercept and slope eliminated by within-patient projection, laboratory offsets `beta ~ N(0, tau^2)` fitted by REML, closed-form posterior, a laboratory with no connecting patient kept at offset 0 with posterior sd `tau_hat`; export to safetensors (no pickle) and ONNX with parity tests; a CUSUM helper with a calibrated threshold. A simulator layer (`vigil_sim/multilab.py`) provides the known truth.
3. **Pre-register and run** `experiments/EXP-K5-001/` (PREREG committed alone; one frozen run).
4. **Accept the result**: H3 failed, the kill rule fired, K5 is not claimed to help (`experiments/EXP-K5-001/CONCLUSION.md`). The module stays as research code at maturity L0 and is wired to nothing.

## Alternatives considered
- Keep the old module and fix its study: rejected, the old estimator is not the one the program describes (ML_PROGRAM §3.5 asks for hierarchical partial pooling) and its design confuses case mix with bias.
- Tune K5 until H3 passes: rejected, the hyper-parameters were fixed in the PREREG and the frozen run is single-use; the honest failure is the outcome.

## Consequences
- `docs/model_cards/MODEL-CARD-K5.md` and its older copy under `docs/models/` are rewritten without the retracted claims.
- STUBS S-009 now states K5's status exactly (estimator and export built, claim not earned, no real data).
- The old class remains importable for an older test and the public import surface; it is labelled legacy.
- Not decided here: whether a different K5 formulation would pass. `CONCLUSION.md` lists what would change the decision.
