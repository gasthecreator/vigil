# Phase 3A Report v2: Model K1 Acceptance Contract Verification

## 1. Verdict Requested
**Request acceptance of Phase 3A: Model K1 Hybrid Mechanistic–Neural State-Space Model** under `docs/MASTER_PLAN.md` v1.2, `docs/ML_PROGRAM.md` §3.1, `docs/REALITY_RULES.md`, `docs/progress/VERDICT-P3A.md`, and `docs/ml/K1-CONTRACT.md`.

All deliverables are verified by independent overseer-authored acceptance contract tests in `tests/acceptance_k1/test_k1_contract.py` (**13/13 passed** without modification).

---

## 2. Phase 3A-2 Gate Table (Conditions K1-A through K1-G)

| Condition / Gate | Requirement | Status | Verification & Evidence Link |
|---|---|---|---|
| **K1-A** (Public API & Contract) | Public API in `vigil_ml/k1.py` with `K1Params`, `PARAM_NAMES`, `sample_prior`, `K1Observations`, `simulate_patient`, `ROUTES`, `risk_from_posterior`, `HybridKineticModelK1` | **MET** | Passed `tests/acceptance_k1/test_k1_contract.py::test_param_names_contract` |
| **K1-A** (Routes: Amortized) | Amortized neural recognition network posterior over `PARAM_NAMES` with zero per-patient optimization | **MET** | Passed `test_route_recovers_truth_with_posterior_intervals[amortized]` (cov 0.90, corr 0.89) & `test_sbc_through_route[amortized]` |
| **K1-A** (Routes: UKF/Particle) | Sequential particle filter over visit schedules evaluating prospective likelihood updates | **MET** | Passed `test_route_recovers_truth_with_posterior_intervals[ukf]` (cov 0.90, corr 0.89) & `test_sbc_through_route[ukf]` |
| **K1-A** (Routes: NUTS Reference) | NumPyro NUTS reference MCMC sampling on the continuous ODE observation likelihood | **MET** | Passed `test_route_recovers_truth_with_posterior_intervals[nuts]` (cov 1.00, corr 0.95) & `test_sbc_through_route[nuts]` |
| **K1-A** (Routes: NPE) | Neural Posterior Estimation (`sbi` NPE_C normalizing flow) evaluated in $<5\,\text{ms}$ | **MET** | Passed `test_route_recovers_truth_with_posterior_intervals[npe]` & `test_routes_agree_with_reference` (NUTS vs NPE diff $< 10\%$) |
| **K1-B** (Zero Label Head) | Removal of direct label head, 0.6/0.4 blend, and hand-set threshold; risk derived strictly from posterior rollout | **MET** | Passed `test_no_direct_label_head` & `test_risk_is_posterior_derived_and_monotone` |
| **K1-C** (Simulation Training) | NPE and amortized networks trained on forward ODE simulations under physiological priors | **MET** | `scripts/train_k1_npe.py` executed; passed `test_routes_agree_with_reference` |
| **K1-D** (Computed Identifiability) | Identifiability analysis computes Fisher Information Matrix eigenvalues over all declared parameters | **MET** | Passed `test_identifiability_is_computed` (eigenvalues spanning $6.27 \times 10^4$ to $9.94 \times 10^{-2}$) |
| **K1-E** (Stub Registry & Reality Audit) | Honest stub accounting in `docs/STUBS.md`; `reality_audit.py` passes with zero findings | **MET** | Passed `python3 scripts/reality_audit.py --require-stub-registry` (0 findings) |
| **K1-F** (Honest S1 Benchmark) | Re-run Study S1 K1 arm, bootstrap CIs, lead time at fixed 5% alert rate, three §13 attempts logged | **MET** | Documented in `reports/ml/S1_SPARSITY/REPORT.md` and Section 4 below |
| **K1-G** (Report v2) | Report citing named acceptance tests and pasting test run output verbatim | **MET** | This report (`docs/progress/PHASE-3A-REPORT.md` v2) |

---

## 3. Verbatim Acceptance Test Suite Output

Executed via `VIGIL_ACCEPTANCE=1 uv run pytest tests/acceptance_k1 -v`:

```
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/gsanni/.gemini/antigravity/scratch/vigil/.venv/bin/python
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: /Users/gsanni/.gemini/antigravity/scratch/vigil
configfile: pyproject.toml
plugins: cov-7.1.0, hypothesis-6.169.3, anyio-4.15.1
collecting ... collecting 13 items                                                            collected 13 items                                                             

tests/acceptance_k1/test_k1_contract.py::test_param_names_contract PASSED [  7%]
tests/acceptance_k1/test_k1_contract.py::test_route_recovers_truth_with_posterior_intervals[amortized] PASSED [ 15%]
tests/acceptance_k1/test_k1_contract.py::test_route_recovers_truth_with_posterior_intervals[ukf] PASSED [ 23%]
tests/acceptance_k1/test_k1_contract.py::test_route_recovers_truth_with_posterior_intervals[nuts] PASSED [ 30%]
tests/acceptance_k1/test_k1_contract.py::test_route_recovers_truth_with_posterior_intervals[npe] PASSED [ 38%]
tests/acceptance_k1/test_k1_contract.py::test_sbc_through_route[amortized] PASSED [ 46%]
tests/acceptance_k1/test_k1_contract.py::test_sbc_through_route[ukf] PASSED [ 53%]
tests/acceptance_k1/test_k1_contract.py::test_sbc_through_route[nuts] PASSED [ 61%]
tests/acceptance_k1/test_k1_contract.py::test_sbc_through_route[npe] PASSED [ 69%]
tests/acceptance_k1/test_k1_contract.py::test_routes_agree_with_reference PASSED [ 76%]
tests/acceptance_k1/test_k1_contract.py::test_risk_is_posterior_derived_and_monotone PASSED [ 84%]
tests/acceptance_k1/test_k1_contract.py::test_no_direct_label_head PASSED [ 92%]
tests/acceptance_k1/test_k1_contract.py::test_identifiability_is_computed PASSED [100%]

============================= 13 passed in 53.34s ==============================
```

---

## 4. Study S1 Benchmark: K1 vs. K3 vs. B4 (Condition K1-F)

Evaluated under pre-registered protocol in `reports/ml/S1_SPARSITY/PREREG.md` across visit depths $V \in \{3, 4, 6, 10, 20\}$ on $N=1,000$ held-out synthetic patients:

| Visit Stratum | Model | IPCW ROC-AUC [95% CI] | Brier Score | ECE | Lead Time (5% alert rate) |
|---|---|---|---|---|---|
| **V=3** | `B4_GradientBoosting` | **0.7550** [0.729, 0.779] | 0.2030 | 0.0505 | 62.8 days |
| **V=3** | `K3_JointModel` | 0.7304 [0.708, 0.762] | 0.2193 | 0.0314 | 54.0 days |
| **V=3** | `K1_Kinetic` | 0.5020 [0.478, 0.529] | 0.3219 | 0.0969 | Non-informative |
| **V=4** | `B4_GradientBoosting` | **0.7853** [0.758, 0.808] | 0.1693 | 0.0421 | 67.1 days |
| **V=4** | `K3_JointModel` | 0.7647 [0.740, 0.787] | 0.1836 | 0.0240 | 54.9 days |
| **V=4** | `K1_Kinetic` | 0.4954 [0.467, 0.516] | 0.2849 | 0.1023 | Non-informative |
| **V=6** | `B4_GradientBoosting` | **0.8065** [0.786, 0.826] | 0.1418 | 0.0359 | 64.3 days |
| **V=6** | `K3_JointModel` | 0.7985 [0.776, 0.816] | 0.1516 | 0.0199 | 55.9 days |
| **V=6** | `K1_Kinetic` | 0.5145 [0.485, 0.538] | 0.2515 | 0.0993 | Non-informative |
| **V=10** | `B4_GradientBoosting` | **0.8142** [0.796, 0.832] | 0.1308 | 0.0344 | 64.3 days |
| **V=10** | `K3_JointModel` | 0.8075 [0.787, 0.826] | 0.1393 | 0.0202 | 55.4 days |
| **V=10** | `K1_Kinetic` | 0.5288 [0.510, 0.546] | 0.2353 | 0.0913 | Non-informative |
| **V=20** | `B4_GradientBoosting` | **0.8141** [0.796, 0.832] | 0.1306 | 0.0346 | 64.3 days |
| **V=20** | `K3_JointModel` | 0.8076 [0.787, 0.826] | 0.1391 | 0.0204 | 55.4 days |
| **V=20** | `K1_Kinetic` | 0.5012 [0.475, 0.521] | 0.2349 | 0.0910 | Non-informative |

### Honest Comparison Summary
Model K1 underperformed both K3 Landmark Joint Modeling and B4 Gradient Boosting at every visit depth, achieving AUC 0.495–0.529 compared to K3's 0.730–0.808 and B4's 0.755–0.814. Without direct label supervision or static multi-modal demographic covariates, standalone kinetic ODE forward rollouts lack the discriminative sharpness of tree ensembles and regularized landmark models on tabular surveillance visits.

### Three Serious §13 Attempts to Improve K1
1. **Attempt 1 (Alternative Growth Formulation & Prior Truncation):**
   - *Design:* Bounding recurrence onset to surveillance horizon ($t_{\text{onset}} \in [30, 240]$) and testing uncoupled Gompertz kinetics.
   - *Result:* Quiescent non-recurrent patients retain wide posterior volume over growth parameters, causing false positive inflation and limiting AUC to 0.495–0.502.
2. **Attempt 2 (Simulation-Based Inference via NPE Normalizing Flows):**
   - *Design:* Training a neural spline flow density estimator (`NPE_C`) on 5,000 forward simulations to resolve multimodality.
   - *Result:* Passed SBC rank uniformity (KS $p = 0.044 > 0.01$) and parameter recovery ($r = 0.89$), but mapping windowed tabular features to interpolated visit vectors resulted in compressed risk dynamic range under sparse sampling ($V=3$).
3. **Attempt 3 (Data-Driven Detection Calibration):**
   - *Design:* Estimating detection threshold $B_{\text{det}}$ dynamically from the training cohort's median recurrence biomarker excess ($B_{\text{det}} \approx 2.5$) instead of using arbitrary constants.
   - *Result:* Removed hand-set thresholds and established monotonicity, but standalone kinetic trajectory hazard cannot match multi-analyte tabular feature baselines.

---

## 5. What Was Made Real vs. What Remains Deferred

### Made 100% Real
- **Continuous 9-State Kinetic ODE System:** Continuous Runge-Kutta 4 numerical integration with closed-form clearance and step-size convergence tests.
- **Four Operational Inference Routes:**
  1. `amortized`: Neural recognition network posterior evaluation in $< 5\,\text{ms}$.
  2. `ukf`: Sequential particle filter over visit schedules.
  3. `nuts`: NumPyro NUTS MCMC exact likelihood gold-standard sampler on CPU.
  4. `npe`: Neural Posterior Estimation via `sbi` normalizing flow.
- **Strict Posterior Risk Derivation:** No direct label head, no hand-set blend, monotone in growth rate and time horizon, data-calibrated detection threshold.
- **Computed Identifiability:** Evaluated from Fisher Information Matrix spectrum over declared parameters across clinical schedules.
- **Independent Acceptance Suite:** 13/13 overseer-authored contract tests passing without modification.

### Deferred (Not Made Real, Strict Stop After Phase 3A)
Per prompt instructions, sub-phases 3B through 3D are **strictly not started**:
- **Phase 3B:** K2 anytime-valid sequential detectors (e-processes, CUSUM), K5 multi-site hierarchical harmonisation, K8 production conformal ensemble.
- **Phase 3C:** K4 deep irregular-time neural zoo (GRU-D, Neural CDE, Continuous-Time Transformer) and Study S4.
- **Phase 3D:** K6 active sensing engine (Study S6) and M12 federated learning trial (Study S10).
All deferred components are registered transparently in `docs/STUBS.md`.
