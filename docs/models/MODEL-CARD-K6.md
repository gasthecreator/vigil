# Model Card: Model K6 — active sensing planner (research module)

**Model identifier:** `MODEL-K6-ACTIVE-SENSING`
**Version:** 2.0.0-research (replaces 1.0.0-alpha, whose evaluation was retracted)
**Maturity:** L0. Research code. **Not wired into ingestion, scoring or any API route.** `DRAFT-UNREVIEWED`.
**Governing documents:** `docs/ML_PROGRAM.md` §3.6 and §6 (S6); `docs/adr/0026-k6-rebuilt-simulation-claim-only.md`; `experiments/EXP-K6-001/`.

## 1. What it is
A planner that, at each visit, chooses the next interval and test panel from a fixed grid by minimising a finite-horizon cost-of-delay objective, given a calibrated multi-horizon hazard `G(u)` (probability that the detectable day falls within `u` days). Implementation: `packages/vigil-ml/vigil_ml/k6.py` (planner, hazard, policies) and `k6_engine.py` (dense-world rollout). The hazard is one XGBoost classifier per horizon plus isotonic calibration; it is persisted as XGBoost JSON text and knot arrays (no pickle). Round-trip identity of `G` is tested in `packages/vigil-ml/tests/test_k6.py`.
**Not built:** posterior expected information gain by nested Monte Carlo on K1; reinforcement learning.

## 2. Intended use
Research on synthetic data, to ask whether a risk-adaptive schedule detects recurrence earlier than fixed, heuristic and risk-triggered schedules at the same assumed cost. **Not for clinical use.** No claim of clinical validity, regulatory clearance or benefit. ESMO guidance (E25) does not recommend routine laboratory tests or tumour markers in asymptomatic patients.

## 3. What was measured (synthetic data only; `experiments/EXP-K6-001/results.json`, `CONCLUSION.md`)
Copied from the script-written `REPORT.md` of frozen run 2 (20 replications; costs in assumed units, not money; delay in days from true clinical recurrence, negative = earlier):
- H1 met: K6 minus the fixed frontier, mean of the two named budgets, **−2.3 days**, Bonferroni interval [−2.4, −2.2].
- H2 met: the same against the risk-triggered frontier, **−0.8 days**, [−1.0, −0.6]. At the cheaper budget the interval includes 0.
- H3 not met: cost saving at the delay of the 3-month schedule 0.312 [0.175, 0.425]; the 25 percent target is not claimed.
- The 2.3-day margin sits on a ~60-day symptomatic-presentation effect (the 3-month named schedule has delay −61.6 days). The P1-only ablation matches the free-panel K6; adding CA 15-3 or CEA did not improve the frontier in this simulator.
- On generator G3 (descriptive, trained on G1) the risk-triggered frontier is earlier than K6 (S2 = +0.3 days [0.1, 0.4]).
- The module is a suggestion with reasons shown and only a simulation claim, as the PREREG already required even if H1 and H2 held.

## 4. Limits
Synthetic data; assumed cost units, not prices; perfect attendance; a shared alert rule that already includes symptom grade ≥ 2, so every panel has detection sensitivity 1.000 in the training table; no real follow-up series. Frozen run 1 used a defective panel table and is not cited.

## 5. What this card replaces
The earlier card claimed a 44 percent visit reduction (20.0 to 11.2), a 49 percent cost reduction ($400 to $204) and a 47.6-day detection delay. Those came from a study that returned literal dictionaries; they are retracted (`reports/ml/RETRACTED/S6_ACTIVE_SENSING/`) and must not be cited.
