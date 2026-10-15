# Phase 3A Report: Model K1 Made Real

## 1. Verdict Requested
**Request acceptance of Phase 3A: Model K1 Hybrid Mechanistic–Neural State-Space Model Made Real** per `docs/MASTER_PLAN.md` v1.2 and `docs/progress/VERDICT-P3.md`.

---

## 2. Phase 3A Exit-Gate Table

| # | Phase 3A Exit Gate Requirement | Status | Evidence Link |
|---|---|---|---|
| 1 | Continuous mechanistic ODE state-space formulation with numerical integration (RK4) tested against closed-form cases and step-size convergence | **MET** | [`packages/vigil-ml/vigil_ml/kinetic_k1.py`](../../packages/vigil-ml/vigil_ml/kinetic_k1.py), [`test_kinetic_k1_real.py`](../../packages/vigil-ml/tests/test_kinetic_k1_real.py) |
| 2 | Genuine model training (`fit`) on patient splits using Adam optimizer with logged training and validation loss histories | **MET** | [`packages/vigil-ml/vigil_ml/kinetic_k1.py`](../../packages/vigil-ml/vigil_ml/kinetic_k1.py#L455-L530), [`test_k1_model_fit_genuine_training`](../../packages/vigil-ml/tests/test_kinetic_k1_real.py) |
| 3 | Prospective risk scoring (`predict_risk`) derived strictly from posterior rollout over burden and onset time, providing credible intervals | **MET** | [`packages/vigil-ml/vigil_ml/kinetic_k1.py`](../../packages/vigil-ml/vigil_ml/kinetic_k1.py#L532-L585), [`test_k1_predict_risk_posterior_and_intervals`](../../packages/vigil-ml/tests/test_kinetic_k1_real.py) |
| 4 | Inference routes: Amortized VI, UKF online filtering with Normalized Innovation Squared (NIS) $\chi^2$ consistency check, and numerical ODE inversion | **MET** | [`packages/vigil-ml/vigil_ml/kinetic_k1.py`](../../packages/vigil-ml/vigil_ml/kinetic_k1.py#L225-L390), [`test_k1_online_ukf_consistency_check`](../../packages/vigil-ml/tests/test_kinetic_k1_real.py) |
| 5 | Real Simulation-Based Calibration (SBC) rank-uniformity test via Kolmogorov-Smirnov test exercising actual ODE dynamics ($p = 0.4588 > 0.01$) | **MET** | [`packages/vigil-ml/vigil_ml/kinetic_k1.py`](../../packages/vigil-ml/vigil_ml/kinetic_k1.py#L640-L690), [`test_k1_sbc_rank_uniformity`](../../packages/vigil-ml/tests/test_kinetic_k1_real.py) |
| 6 | Real parameter recovery for doubling times ($r = 0.8706$, 90% CI coverage = $88.0\% \ge 70\%$) and structural identifiability analysis | **MET** | [`packages/vigil-ml/vigil_ml/kinetic_k1.py`](../../packages/vigil-ml/vigil_ml/kinetic_k1.py#L692-L780), [`test_k1_parameter_recovery_real`](../../packages/vigil-ml/tests/test_kinetic_k1_real.py) |
| 7 | Study S1 evaluated with K1 arm under pre-registered protocol across visit depths $V \in \{3, 4, 6, 10, 20\}$ | **MET** | [`reports/ml/S1_SPARSITY/REPORT.md`](../../reports/ml/S1_SPARSITY/REPORT.md), [`reports/ml/BENCHMARK_REPORT.md`](../../reports/ml/BENCHMARK_REPORT.md) |
| 8 | Model card documenting differential equations, empirical metrics, real vs estimated components, and identifiability limitations | **MET** | [`docs/models/MODEL-CARD-K1.md`](../models/MODEL-CARD-K1.md) |
| 9 | Stub registry updated honestly with S-001, S-002, S-003 resolved | **MET** | [`docs/STUBS.md`](../STUBS.md) |
| 10| Reality audit (`scripts/reality_audit.py --require-stub-registry`) passes with zero findings | **MET** | Automated CI verification |

---

## 3. Commands Run and Verification Evidence

### 3.1 Reality Audit Verification
```bash
python3 scripts/reality_audit.py --require-stub-registry
```
**Output:**
```
Reality audit passed: no hard-coded results, no-op fits, toy validations or phantom classes found.
```

### 3.2 Full Test Suite Execution
```bash
uv run pytest
```
**Output:**
```
collected 106 items

apps/api/tests/test_api_endpoints.py ....                                [  3%]
apps/api/tests/test_e2e_simulation.py .                                  [  4%]
packages/vigil-core/tests/test_analytes.py ........                      [ 12%]
packages/vigil-core/tests/test_fhir.py ...                               [ 15%]
packages/vigil-core/tests/test_units.py .........                        [ 23%]
packages/vigil-sim/tests/test_calibration.py ....                        [ 27%]
packages/vigil-sim/tests/test_generators.py .....                        [ 32%]
packages/vigil-eval/tests/test_evaluation_components.py ......           [ 37%]
packages/vigil-eval/tests/test_leakage.py ...........                    [ 48%]
packages/vigil-eval/tests/test_metrics.py ......                         [ 53%]
packages/vigil-ml/tests/test_baselines.py .....                          [ 58%]
packages/vigil-ml/tests/test_baselines_sanity.py ....                    [ 62%]
packages/vigil-ml/tests/test_features.py ..                              [ 64%]
packages/vigil-ml/tests/test_joint_model.py ..                           [ 66%]
packages/vigil-ml/tests/test_joint_model_validation.py ...               [ 68%]
packages/vigil-ml/tests/test_kinetic_k1_real.py .........                [ 77%]
packages/vigil-ml/tests/test_organ_susceptibility.py ..                  [ 79%]
packages/vigil-ml/tests/test_phase3_models.py ...........                [ 89%]
packages/contracts/tests/test_loaders.py .....                           [ 94%]
tests/test_reality_audit.py ...                                          [ 97%]
tests/test_report_traceability.py ...                                    [100%]

======================== 106 passed, 1 warning in 14.85s =======================
```

### 3.3 Study S1 Benchmark Results (K1 Performance vs Baselines)
Evaluated across $N=1,000$ held-out synthetic patients under pre-registered protocol:
- **$V=3$ (Extreme Sparsity):** IPCW ROC-AUC = 0.7077 [0.682, 0.738], Brier = 0.2030, Net Benefit = 0.3112
- **$V=4$:** IPCW ROC-AUC = 0.7549 [0.731, 0.775], Brier = 0.1770, Net Benefit = 0.2520
- **$V=6$:** IPCW ROC-AUC = 0.7823 [0.765, 0.804], Brier = 0.1565, Net Benefit = 0.1985
- **$V=10$ (Standard Surveillance):** IPCW ROC-AUC = 0.7953 [0.776, 0.818], Brier = 0.1487, Net Benefit = 0.1724, Lead Time = 38.5 days at 5% alert rate, Latency p95 CPU = 0.84 ms
- **$V=20$ (Dense Surveillance):** IPCW ROC-AUC = 0.7995 [0.780, 0.815], Brier = 0.1485, Net Benefit = 0.1718

---

## 4. Claims Ledger

| Claim | Quantitative / Qualitative Scope | Supporting Evidence |
|---|---|---|
| Continuous RK4 Integrator Precision | Closed-form marker clearance matches analytical exponential decay with relative error $< 10^{-4}$ | `packages/vigil-ml/tests/test_kinetic_k1_real.py::test_kinetic_ode_closed_form_clearance` |
| Integrator Step-Size Convergence | Halving integration step size decreases truncation error by order $\ge O(\Delta t^2)$ | `packages/vigil-ml/tests/test_kinetic_k1_real.py::test_kinetic_ode_step_size_convergence` |
| Genuine Training | `fit()` decreases training loss across epochs via Adam gradient descent | `packages/vigil-ml/tests/test_kinetic_k1_real.py::test_k1_model_fit_genuine_training` |
| Filter Consistency | UKF Normalized Innovation Squared (NIS) falls within 95% $\chi^2$ confidence bounds | `packages/vigil-ml/tests/test_kinetic_k1_real.py::test_k1_online_ukf_consistency_check` |
| SBC Rank Uniformity | Rank statistics satisfy KS test with $p = 0.4588 > 0.01$ | `packages/vigil-ml/tests/test_kinetic_k1_real.py::test_k1_sbc_rank_uniformity` |
| Parameter Recovery | Tumor doubling time recovery Pearson $r = 0.8706 > 0.70$, 90% CI coverage $= 88.0\% \ge 70\%$ | `packages/vigil-ml/tests/test_kinetic_k1_real.py::test_k1_parameter_recovery_real` |
| CPU Inference Latency | Model K1 p95 CPU latency is 0.84 ms, comfortably within the $< 10.0\text{ ms}$ budget | `reports/ml/BENCHMARK_REPORT.md` |

---

## 5. Deviations & ADRs
- **Thread Isolation for Standalone Scripts:** On macOS Apple Silicon, PyTorch multithreading collides with OpenMP and the Python GIL. Environment variables `OMP_NUM_THREADS=1` and `torch.set_num_threads(1)` were added to `scripts/run_benchmarks.py` to prevent thread deadlocks.
- **Sub-phase Split:** In strict accordance with Master Plan v1.2, this report covers Phase 3A only. Sub-phases 3B, 3C, and 3D are NOT started.

---

## 6. Failures, Dead Ends, and Identifiability Limits
1. **Collinearity of Deep Organ Shedding ($s_{\text{loc}}, s_{\text{lung}}, s_{\text{brain}}$):** Structural identifiability analysis revealed near-zero Fisher information eigenvalues for individual deep organ compartment shedding rates when only blood-based biomarkers are available without organ-specific damage enzymes. Individual compartment shedding cannot be uniquely recovered from serial CA 15-3 alone; regularized shrinkage priors or pooled organ priors must be enforced.
2. **Uncalibrated Sigmoid Thresholding (ECE 0.1412):** While K1 achieves strong discrimination (AUC 0.7953), its raw calibration error (ECE 0.1412) is higher than K3 (ECE 0.0202) due to the sharp sigmoid transition on future latent tumor mass. Post-hoc conformal temperature scaling and Platt scaling are deferred to Phase 3B.

---

## 7. Blockers Requiring Human Action
- *None for Phase 3A.* External restricted datasets remain bounded by synthetic loaders and data agreements (`docs/data/ACCESS.md`).

---

## 8. Defect & Finding Closure
- **S-001 (K1 fit/predict_risk overhaul):** RESOLVED.
- **S-002 (K1 inference routes):** RESOLVED.
- **S-003 (K1 SBC & parameter recovery overhaul):** RESOLVED.
