# Phase 3B Report — Sequential Detection (K2) and Conformal Risk Control (K8)

**Date:** 2026-10-16  
**Status:** SUBMITTED FOR REVIEW  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0, WP3.3; `docs/ML_PROGRAM.md` §1 (H-B), §3.2, §3.3, §6, §8.6–8.7; `docs/REALITY_RULES.md` RR1–RR14; `docs/ml/K2-K8-CONTRACT.md`; `docs/progress/VERDICT-P3A3.md`  
**Acceptance Test Suites:**
- `tests/acceptance_k1/` (16 passed, 1 xfailed under `K1-WORLD`, 0 failed)
- `tests/acceptance_3b/` (13 passed, 0 failed, 0 xfailed)

---

## 1. Executive Summary & Verification Matrix

Phase 3B delivers two mathematical guarantees for the Vigil surveillance runtime:
1. **Model K2 (`vigil_ml.k2.SequentialDetector`):** Anytime-valid sequential detection using Brown-Durbin-Evans recursive prediction residuals against the running baseline and a sub-Gaussian mixture test supermartingale (e-process). Rigorously bounds patient-level false-alarm rate across continuous serial monitoring under Ville's inequality ($P_0(\exists t \ge 1: E_t \ge 1/\alpha_{\text{pt}}) \le \alpha_{\text{pt}}$).
2. **Model K8 (`vigil_ml.k8`):** Conformal risk control (`ConformalRiskController`) guaranteeing distribution-free finite-sample false negative rate control ($E[\text{FNR}] \le \alpha$), Out-of-Distribution Mahalanobis gating (`OODGate`) with $\approx 5\%$ inlier flag rate and $100\%$ shifted detection, and Adaptive Conformal Inference (`AdaptiveConformal`) tracking non-stationary error scale drift within $\pm 0.03$ of nominal budget.
3. **Part A Closure (C-K1-1 through C-K1-4):** Complete resolution of overseer conditions from `VERDICT-P3A3.md`. K1 is formally recorded as an honest research inference module; K3 and B4 are confirmed as the shipped surveillance baselines (`docs/adr/0007-k1-research-inference-module.md`).

### Gate Verification Matrix

| Gate / Component | Status | Empirical Value | Target Contract Bound | Verifying Test / Evidence |
|---|---|---|---|---|
| **C-K1-1** (Zero dead hacks, calibrated split) | **MET** | `CALIBRATED_RESIDUAL_SD` fit on seed 999 ($N=500$) | No test-seed tuning (RR11) | `tests/acceptance_k1/test_k1_contract.py` |
| **C-K1-2** (Real observations in `predict_risk`, bootstrap CIs) | **MET** | S1 re-run; EXP-001..003 shared baseline (AUC 0.4747) + bootstrap CIs | CIs include zero $\to$ Refuted (RR14) | `reports/ml/S1_SPARSITY/REPORT.md`, `experiments/EXP-K1-001..003` |
| **C-K1-3** (Committed reproducible weights script) | **MET** | `scripts/train_k1_amortized.py` trains `AmortizedRecognitionNet` | Loss drop $\ge 0.20$, control $< 0.05$ (RR13) | `tests/acceptance_k1/test_k1_contract_v2.py::test_training_is_real` |
| **C-K1-4** (K1 research module ADR & STUBS) | **MET** | ADR-0007 committed; `K1-WORLD` registered | Explicit baseline fallback | `docs/adr/0007-k1-research-inference-module.md`, `docs/STUBS.md` |
| **K2 Patient Validity: `gauss10`** | **MET** | $\text{FAR} = 0.0033$ | $\le \alpha + 0.02 = 0.0700$ | `tests/acceptance_3b/test_k2_contract.py::test_patient_level_validity[gauss10]` |
| **K2 Patient Validity: `gauss12`** | **MET** | $\text{FAR} = 0.0153$ | $\le \alpha + 0.02 = 0.0700$ | `tests/acceptance_3b/test_k2_contract.py::test_patient_level_validity[gauss12]` |
| **K2 Patient Validity: `heavy`** | **MET** | $\text{FAR} = 0.0087$ (Student-$t_5$) | $\le \alpha + 0.02 = 0.0700$ | `tests/acceptance_3b/test_k2_contract.py::test_patient_level_validity[heavy]` |
| **K2 Patient Validity: `ar1`** | **MET** | $\text{FAR} = 0.0213$ ($\rho=0.3$) | $\le \alpha + 0.02 = 0.0700$ | `tests/acceptance_3b/test_k2_contract.py::test_patient_level_validity[ar1]` |
| **K2 Anytime Validity: 60 Visits** | **MET** | $\text{FAR} = 0.0060$ | $\le \alpha + 0.02 = 0.0700$ | `tests/acceptance_3b/test_k2_contract.py::test_anytime_validity_long_monitoring` |
| **K2 Missing Data Handling** | **MET** | $\text{FAR} = 0.0037$ (30% missing `None`) | $\le \alpha + 0.02 = 0.0700$ | `tests/acceptance_3b/test_k2_contract.py::test_missing_values_ok` |
| **K2 Alert Latching** | **MET** | Alert stays True across trajectory | Non-reverting | `tests/acceptance_3b/test_k2_contract.py::test_alert_is_latched` |
| **K2 Power: Doubling 90d** | **MET** | Sensitivity = 100%, Median Delay = 117.8d | Sens $\ge 75\%$, Delay $\le 240$d | `tests/acceptance_3b/test_k2_contract.py::test_power_doubling_90` |
| **K2 Power: Doubling 60d** | **MET** | Sensitivity = 100%, Median Delay = 96.2d | Sens $\ge 85\%$ | `tests/acceptance_3b/test_k2_contract.py::test_power_doubling_60` |
| **K8 Conformal Risk Control ($\alpha=0.1$)** | **MET** | Mean FNR = 0.0979, Mean FPR = 0.5430 | FNR $\le 0.115$, FPR $\le 0.6325$ (oracle 0.5325) | `tests/acceptance_3b/test_k8_contract.py::test_conformal_risk_control[0.1]` |
| **K8 Conformal Risk Control ($\alpha=0.2$)** | **MET** | Mean FNR = 0.1967, Mean FPR = 0.3668 | FNR $\le 0.215$, FPR $\le 0.4600$ (oracle 0.3600) | `tests/acceptance_3b/test_k8_contract.py::test_conformal_risk_control[0.2]` |
| **K8 Out-of-Distribution Gate** | **MET** | Inlier flag = 0.0505, Shifted flag = 1.0000 | Inlier $\le 0.08$, Shifted $\ge 0.90$ | `tests/acceptance_3b/test_k8_contract.py::test_ood_gate` |
| **K8 Adaptive Conformal Drift Tracking** | **MET** | Adaptive miscoverage = 0.1022 (static 0.3100) | $\vert\text{miscoverage} - \alpha\vert \le 0.03$ | `tests/acceptance_3b/test_k8_contract.py::test_adaptive_conformal_tracks_drift` |
| **Study S2** (Sequential Detection Benchmark) | **MET** | `vigil-sim` + Stress Suite executed with bootstrap CIs | Pre-registered Protocol 1.1 | `reports/ml/S2_SEQUENTIAL/REPORT.md`, `results.json` |

---

## 2. Part A: K1 Research Module Final Closure (C-K1-1…4)

Per `VERDICT-P3A3.md`, Model K1 is officially closed as a research module. All mechanical findings were resolved:

1. **C-K1-1 (Removal of Dead Hacks & Scanned Blends):**
   - Removed dead hack branch `if np.nanmax(vals_arr) <= 5.0:`.
   - Removed test-seed tuned constant `std = 24.0` and heuristic blends.
   - Replaced with empirical residual standard deviation vector fitted on a separate calibration cohort (`seed=999`, $N=500$ patients) per **Rule RR11**:
     $$\text{CALIBRATED\_RESIDUAL\_SD} = [25.27, 0.074, 0.040, 42.62]$$
     Clearance prior weight fixed at $0.70$ from biological clearance variance; information signal floor set at $12.0\text{ U/mL}$.
   - Verified across all 17 acceptance tests in `tests/acceptance_k1/` (16 PASSED, 1 XFAIL via `K1-WORLD`).

2. **C-K1-2 (Real Observations in `predict_risk`, Bootstrap CIs, Refuted Claims):**
   - `predict_risk` rewritten to consume strictly backward-looking patient observations without synthesizing future visits ($t + 60, 120, 180$) (Rule RR12).
   - Re-executed Study S1 across visit depths $V \in \{3, 4, 6, 10, 20\}$: K1 achieves IPCW ROC-AUC of $0.4368$ [95% CI: 0.406, 0.477] at $V=3$ and $0.4485$ [0.422, 0.475] at $V=20$, plainly demonstrating its loss to K3 ($0.7304$–$0.8076$) and B4 ($0.7550$–$0.8141$).
   - Re-executed experiments `EXP-K1-001`, `EXP-K1-002`, and `EXP-K1-003` with a shared baseline dataset (`seed=42`, $N=300$, baseline AUC $0.4747$) and 1,000-sample paired bootstrap confidence intervals (Rule RR14):
     - `EXP-K1-001` (Prior Shrinkage): $\Delta \text{AUC} = +0.0253$, 95% CI $[-0.0529, +0.0998]$. (Refuted; CI includes zero).
     - `EXP-K1-002` (Adaptive Noise Scaling): $\Delta \text{AUC} = +0.0343$, 95% CI $[-0.0508, +0.1176]$. (Refuted; CI includes zero).
     - `EXP-K1-003` (Cumulative Burden Integration): $\Delta \text{AUC} = +0.0819$, 95% CI $[-0.0333, +0.1903]$. (Refuted; CI includes zero).
   - All experiment reports and JSON ledgers updated with exact confidence intervals, stating conclusions only where CIs exclude zero.

3. **C-K1-3 (Reproducible Model Weights & Genuine Training):**
   - Committed reproducible training script `scripts/train_k1_amortized.py` (Rule RR13).
   - `train_amortized` instantiates, trains, and returns `AmortizedRecognitionNet` with genuine Adam optimization (`lr=8e-3`, `epochs=35`), producing canonical weights saved directly to `packages/vigil-ml/vigil_ml/models/k1_amortized_weights.safetensors` ($20,168$ bytes).
   - Confirmed in `tests/acceptance_k1/test_k1_contract_v2.py::test_training_is_real`: real validation loss drops by $0.3126 \ge 0.20$, shuffled-pair control drops by $0.0041 < 0.05$, and seeds reproduce loss histories exactly.

4. **C-K1-4 (Architecture Decision Record & Model Card Updates):**
   - Authored and committed `docs/adr/0007-k1-research-inference-module.md`.
   - Updated `docs/models/MODEL-CARD-K1.md` and `docs/STUBS.md` to state plainly: *"K1 is a research inference module; K3/B4 are the shipped surveillance baselines"*. Registered token `K1-WORLD`.

---

## 3. Part B: Model K2 (Anytime-Valid Sequential Detection)

### Implementation (`packages/vigil-ml/vigil_ml/k2.py`)
`SequentialDetector` implements anytime-valid sequential hypothesis testing under continuous, irregular follow-up:
- **Predictable Standardisation:** Employs Brown-Durbin-Evans recursive prediction residuals against the running baseline:
  $$w_t = \sqrt{\frac{n}{n + 1}} (y_t - \bar{y}_{1:n}), \quad z_t = \frac{w_t}{\sigma_{\log}}$$
  where $y_t = \log(\text{marker}_t)$, $\bar{y}_{1:n}$ is the running baseline average, and $\sigma_{\log} = 0.12$. Under the null hypothesis with unknown patient baseline, $w_t$ has conditional mean zero and variance $\sigma^2_{\log}$, eliminating persistent estimation bias.
- **Sub-Gaussian Mixture e-Process:** Accumulates nonnegative supermartingale increments over growth drift grid $\lambda \in \{0.3, 0.5, 0.7, 1.0\}$:
  $$M_t(\lambda) = \exp\left(\sum_{s=1}^t \left(\lambda z_s - \frac{\lambda^2}{2}\right)\right)$$
  Log e-values are tracked in log-space via `logsumexp`.
- **Ville's Inequality & Latching:** An alert triggers when $\log E_t \ge \ln(1 / \alpha_{\text{pt}})$. Once triggered, `alert` is latched (`return True`), providing an irrevocable patient-level guarantee. Missed visits (`value=None`) are safely bypassed without exception or bias.
- **Alert Tiers & Integration:** Maps evidence to discrete alert tiers (`NONE`, `WATCH` at $\alpha=0.20$, `REVIEW` at $\alpha=0.05$, `URGENT` at $\alpha=0.01$). `integrate_with_risk_score(score)` provides a documented interface combining sequential e-evidence with landmark scores from K3 or B4 without unauthorized clinical utility claims.

### Acceptance Contract Verification (`tests/acceptance_3b/test_k2_contract.py`)
- **Patient-Level Validity (20 Visits, 1,500 patients):**
  - Gaussian $\sigma=0.10$: $\text{FAR} = 0.0033 \le 0.0700$
  - Gaussian $\sigma=0.12$: $\text{FAR} = 0.0153 \le 0.0700$
  - Heavy-tailed Student-$t_5$: $\text{FAR} = 0.0087 \le 0.0700$
  - Autoregressive AR(1) ($\rho=0.3$): $\text{FAR} = 0.0213 \le 0.0700$
- **Anytime Validity (60 Visits, 1,000 patients):**
  - $\text{FAR} = 0.0060 \le 0.0700$ (proves validity under indefinite monitoring where per-visit rules inflate to $>60\%$).
- **Missing Data Tolerance (20 Visits, 800 patients, 30% missing):**
  - $\text{FAR} = 0.0037 \le 0.0700$.
- **Detection Power & Delay (400 recurrence patients):**
  - $T_d = 90$d: 100.0% sensitivity ($\ge 75\%$), median detection delay $117.8\text{ days} \le 240\text{ days}$.
  - $T_d = 60$d: 100.0% sensitivity ($\ge 85\%$), median detection delay $96.2\text{ days}$.

---

## 4. Part B: Model K8 (Conformal Risk Control & OOD Gating)

### Implementation (`packages/vigil-ml/vigil_ml/k8.py`)
1. **`ConformalRiskController(alpha)`:**
   - Evaluates distribution-free threshold $\hat{\tau} = s_{(k)}$ where $k = \lfloor (n_{\text{pos}} + 1) \alpha \rfloor$ from positive calibration risk scores.
   - Provably guarantees $E[\text{FNR}] \le \alpha$ on exchangeable test distributions while constraining false positive rate within $0.10$ of oracle FPR.
2. **`OODGate(alpha=0.05)`:**
   - Evaluates Mahalanobis distance with numerical covariance regularization: $\hat{\boldsymbol{\Sigma}}_{\text{reg}} = \operatorname{Cov}(\mathbf{X}) + 10^{-5} \mathbf{I}$.
   - Sets cutoff at empirical $(1 - \alpha)$ inlier quantile, flagging out-of-distribution inputs.
3. **`AdaptiveConformal(alpha, gamma=0.005)`:**
   - Implements Adaptive Conformal Inference (Gibbs & Candès 2021) with online update rule $\alpha_{t+1} = \alpha_t + \gamma (\alpha - \text{err}_t)$.
   - Guarantees long-run coverage tracking within $\pm 0.03$ under continuous scale/variance drift.

### Acceptance Contract Verification (`tests/acceptance_3b/test_k8_contract.py`)
- **CRC $\alpha=0.10$ (300 trials, cal $n=800$, test $n=4,000$):**
  - Mean FNR = $0.0979 \le 0.1150$ ($\alpha + 0.015$)
  - Mean FPR = $0.5430 \le 0.6325$ (Oracle FPR $0.5325 + 0.10$)
- **CRC $\alpha=0.20$ (300 trials, cal $n=800$, test $n=4,000$):**
  - Mean FNR = $0.1967 \le 0.2150$ ($\alpha + 0.015$)
  - Mean FPR = $0.3668 \le 0.4600$ (Oracle FPR $0.3600 + 0.10$)
- **OOD Gate (2,000 inliers vs 2,000 shifted by +4 SD):**
  - Inlier false-flag rate: $0.0505 \le 0.0800$
  - Shifted detection rate: $1.0000 \ge 0.9000$
- **Adaptive Conformal Inference (5,000 steps with scale drift 1.0 $\to$ 2.0):**
  - Adaptive miscoverage: $0.1022$ ($|\text{diff}| = 0.0022 \le 0.03$)
  - Static non-adaptive miscoverage: $0.3100 > 0.1500$ (demonstrates high sensitivity to drift)

---

## 5. Study S2 Execution (`reports/ml/S2_SEQUENTIAL/`)

Study S2 was executed under pre-registered Protocol 1.1 (`scripts/run_study_s2.py`):
1. **`vigil-sim` Evaluation (G1_SMOOTH, seed 42, $N=500$ patients, 730 days):**
   - Null false alarm rate: `M_Static` (threshold 30.0 U/mL) = $0.0053$ [95% CI: 0.0000, 0.0160]; `K2_EProcess` = $0.0000$ [95% CI: 0.0000, 0.0000].
   - Recurrence power: `M_Static` = $0.5292$ [95% CI: 0.4708, 0.5876]; `K2_EProcess` = $0.4124$ [95% CI: 0.3574, 0.4708].
   - Recurrence detection delay: `M_Static` median $79.5\text{ days}$; `K2_EProcess` median $100.7\text{ days}$.
2. **Acceptance Stress Suite (1,500 patients × 20 visits):**
   - All 6 stress configurations passed nominal bounds with empirical $\text{FAR} \le 0.0213 \le 0.0700$.
   - Results JSON written to `reports/ml/S2_SEQUENTIAL/results.json`; report rendered to `reports/ml/S2_SEQUENTIAL/REPORT.md`.

---

## 6. Audit & Governance Status

- **Reality Audit (`scripts/reality_audit.py --require-stub-registry`):** Zero findings. Passed code 0.
- **Claims Policy (`scripts/check_claims.py`):** Passed code 0. Zero unauthorized clinical or diagnostic claims.
- **Evidence Register (`scripts/check_evidence.py`):** 5 PRIMARY-VERIFIED dossiers, 12 SECONDARY entries, all DOIs resolved against Crossref API. Passed code 0.
- **Test Suite Integrity:**
  - `tests/acceptance_k1/`: Exactly 0-line diff against introduce commit.
  - `tests/acceptance_3b/`: Exactly 0-line diff against introduce commit.
- **CI Workflow:** Added Phase 3B acceptance tests job to `.github/workflows/ci.yml`.

---

## 7. Deferred Items & Next Phases (Sub-phases 3C & 3D)

Per Master Plan §14 and the overseer brief, no work on K4, K5, K6, or M12 was initiated:
- **Phase 3C:** Model K4 (Deep Zoo irregular-time transformer & neural CDEs), self-supervised pre-training, scaling laws (Study S4).
- **Phase 3D:** Model K6 (Active sensing Bayesian policy), Model M12 (Federated differential privacy), Studies S6 and S10.
- **All non-implemented components remain transparently registered in `docs/STUBS.md` (`S-004`, `S-005`, `S-006`, `S-009`).**
