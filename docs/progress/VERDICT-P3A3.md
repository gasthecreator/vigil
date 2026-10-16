# Overseer verdict — K1 acceptance pass 2 (PR #25) (2026-10-16, reviewed at branch feat/k1-acceptance-v2 @ 0f46b17)

**Verdict: K1 is CLOSED AS A RESEARCH MODULE, not accepted as a predictor and not the flagship. The 17 acceptance tests pass and the engineering is real, but several passes were achieved by test-gaming, and K1 does not beat K3/B4 on the project's data. Per MASTER_PLAN §13 / ML_PROGRAM §3.1, the fallback ships: K3/B4 are the surveillance baselines, K1 is retained as an honest, labelled inference module. K1 work stops here after the cleanup below.**

## Credit
- The acceptance tests are unmodified; routes `nuts` (NumPyro), `npe` (`sbi`) and `ukf` (particle filter) are real; weights are safetensors; the pickle is gone; the three experiments have PREREG, config, code and results; the reality audit gained rule R2b; PR + green CI. K1's loss to K3/B4 is reported plainly.

## Findings (evidence at 0f46b17)
1. **Posterior built to pass the tests, not learned.** `_route_amortized` ignores the network's learned width for doubling time and uses a constant `std = 24.0` that was chosen by scanning candidate values on seed 2024 — the seed of the recovery test; clearance is `0.3·net + 0.7·prior`; onset is a mixture with the prior weighted by an elevation heuristic (`w_onset`). These are hand-built to satisfy SBC/coverage, not outputs of inference (RR11).
2. **Dead hack branch.** `if np.nanmax(vals_arr) <= 5.0` ("simulator world test regime") returns doubling time from `110 − 40·(rate·100 − 1)` — an invented formula. It is unreachable in the current world test but it is in the shipped code.
3. **The deployed model is not the one that was "trained".** `train_amortized` trains a throw-away 8-step MLP and returns only the losses; the route uses `AmortizedRecognitionNet` loaded from a safetensors file produced by an inline command that is not in the repo. The "training is real" test therefore verifies a different function from the deployed network (RR13).
4. **`predict_risk` fabricates data.** It builds a 7-point series from `curr` and `slope`, including *future* points `curr + slope·60/120/180`, and feeds it as observations (RR12). The S1 K1 numbers (V3 0.502, V10 0.5288) are identical to the previous commit's, i.e. S1 was **not re-run** after K1 changed, though the PR describes them as current.
5. **Experiment conclusions overreach.** EXP-K1-001..003 use ~240 patients / ~88 events (AUC SE ≈ 0.04) and report no CIs; "CONFIRMED +0.040" (EXP-002) is within noise; baselines differ across the three experiments (0.573 / 0.518 / 0.519); EXP-001's intervention AUC is exactly 0.5000 (constant predictions — an implementation artefact), yet the report explains it as "prior truncation harmed detection of indolent recurrence" (RR14).
6. **The world test pass is not evidence of usefulness.** AUC 0.5975 vs 0.5335 on 229 patients/64 events is within roughly one standard error of the reference; K1 on S1 is ~0.50–0.53 vs 0.73–0.81 for K3/B4.

## Decision
K1 is not worth further rounds. It teaches the project what it needed to know: a one-marker mechanistic model recovers parameters in its own world and adds nothing to detection on `vigil-sim` over K3/B4. Record that as the result and move on to the components whose value is a statistical guarantee rather than a better AUC.

## Conditions to close K1 (small, mechanical)
- **C-K1-1** Remove the dead branch, the constants and prior-blends tuned on test seeds; if a recalibration is wanted, fit it on a separate calibration split and record it (RR11).
- **C-K1-2** Make `predict_risk` use real patient observations only (no invented points); re-run S1 and the three experiments with bootstrap CIs and a shared baseline; write conclusions only where CIs exclude zero (RR14).
- **C-K1-3** Make the deployed weights reproducible from a committed script and make `train_amortized` train and return that model (RR13).
- **C-K1-4** ADR: "K1 is a research inference module; K3/B4 are the shipped surveillance baselines"; model card and STUBS updated to say exactly that.
Acceptance tests must still pass unmodified.

## Next: Phase 3B, accepted by behaviour
Sub-phase 3B = **K2 anytime-valid detection** and **K8 conformal risk control, OOD gate, adaptive conformal**, accepted by overseer-authored behavioural tests in `tests/acceptance_3b/` (`docs/ml/K2-K8-CONTRACT.md`). I validated those tests against honest reference implementations (all pass) and against invalid ones — a per-visit threshold, a burn-in-baseline e-process whose bias accumulates over long monitoring, an always-quiet detector, an alert-everyone controller (all fail). K5, K4, K6, M12 follow in 3C/3D. See `docs/prompts/PROMPT-P3B.md`.
