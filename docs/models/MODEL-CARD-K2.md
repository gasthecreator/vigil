# Model Card: Model K2 — Anytime-Valid Sequential Detection Engine

**Model Identifier:** `MODEL-K2-SEQUENTIAL-DETECTOR`  
**Model Version:** 1.1.0-alpha  
**Date:** 2026-10-16  
**Module Reference:** `packages/vigil-ml/vigil_ml/k2.py` (`vigil_ml.k2.SequentialDetector`)  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-B), §3.2, §6; `docs/ml/K2-K8-CONTRACT.md`  
**Acceptance Test Suite:** `tests/acceptance_3b/test_k2_contract.py` (all 9 contract tests passing)  
**Study Reference:** [`reports/ml/S2_SEQUENTIAL/REPORT.md`](../../reports/ml/S2_SEQUENTIAL/REPORT.md)  

---

## 1. Model Overview and Intended Use
Model K2 solves the fundamental multi-testing hazard inherent in longitudinal oncology surveillance. In standard clinical practice, static threshold rules (e.g. CA 15-3 $\ge 30\text{ U/mL}$ or per-visit nominal cutoffs) are re-evaluated at every outpatient follow-up visit (up to 15–20 visits over 5 years). This serial repeated testing severely inflates the cumulative patient-level false alarm rate:

$$1 - (1 - \alpha)^K \gg \alpha$$

For example, with $K=20$ visits at nominal $\alpha=0.05$, the unadjusted false alarm rate reaches $1 - 0.95^{20} = 64.2\%$.

Model K2 formulates serial surveillance as an anytime-valid sequential hypothesis testing game using Nonnegative Test Supermartingales (e-processes) and Ville's Inequality. It mathematically guarantees that the cumulative probability of ever raising a false alarm over a patient's entire lifetime follow-up under indefinite monitoring is bounded by the nominal budget $\alpha_{\text{pt}}$.

---

## 2. Mathematical Formulation & Martingale Mechanics

### Recursive Standardisation Against Running Baseline
A known pitfall of serial surveillance is that estimating a patient's baseline from initial visits leaves a persistent bias that accumulates over long monitoring and breaks validity. To prevent this, K2 uses the Brown-Durbin-Evans (1975) recursive prediction residual against the running baseline:

$$w_t = \sqrt{\frac{n}{n + 1}} \left(y_t - \bar{y}_{1:n}\right)$$

where $y_t = \log(\text{marker}_t)$, $n$ is the count of previous observations ($n \ge \text{burn\_in} = 3$), and $\bar{y}_{1:n} = \frac{1}{n} \sum_{i=1}^n y_i$. Under the null hypothesis of clinical quiescence with unknown baseline level, $w_t$ has conditional mean zero and variance $\sigma^2_{\log}$, eliminating persistent estimation bias.

The standardized increment is:
$$z_t = \frac{w_t}{\sigma_{\log}}$$

### Sub-Gaussian Mixture e-Process
For each candidate growth rate $\lambda \in \{0.3, 0.5, 0.7, 1.0\}$, sub-Gaussian supermartingale increments are accumulated:

$$M_t(\lambda) = \exp\left(\sum_{s=1}^t \left(\lambda z_s - \frac{\lambda^2}{2}\right)\right)$$

The anytime-valid evidence is the uniform mixture over the candidate growth rates:

$$E_t = \frac{1}{|\mathcal{G}|} \sum_{\lambda \in \mathcal{G}} M_t(\lambda)$$

In logarithmic space:
$$\log E_t = \operatorname{logsumexp}\left(\log \mathbf{w} + \log \mathbf{M}_t\right)$$

### Ville's Maximal Inequality & Latching
By Ville's inequality, for any stopping time $\tau$ or continuous monitoring horizon:

$$P_0\left(\exists t \ge 1 : E_t \ge \frac{1}{\alpha_{\text{pt}}}\right) \le \alpha_{\text{pt}}$$

When $\log E_t \ge \log(1 / \alpha_{\text{pt}})$, the detector raises an alert that remains latched (`alert = True`), guaranteeing non-reverting patient-level detection.

---

## 3. Calibrated Alert Tiers & Score Integration

Discrete alert tiers are mapped via exact Ville thresholds without ad-hoc inflation:
- **Tier 0: None ($E_t < 5$):** Stationary quiescence; continue routine surveillance.
- **Tier 1: Watch ($\alpha_{\text{pt}} = 0.20$, $\log E_t \ge \ln(5) \approx 1.609$):** Early trend detected; recommend earlier re-test window.
- **Tier 2: Review ($\alpha_{\text{pt}} = 0.05$, $\log E_t \ge \ln(20) \approx 2.996$):** Confirmed upward drift; clinician review.
- **Tier 3: Urgent ($\alpha_{\text{pt}} = 0.01$, $\log E_t \ge \ln(100) \approx 4.605$):** High conviction of rapid metastatic doubling; trigger diagnostic imaging protocol.

### Landmark Risk Score Integration
`SequentialDetector.integrate_with_risk_score(score)` provides a clean, documented interface connecting the sequential e-process evidence with landmark risk scores from K3 or B4, yielding tiered recommendations (`RECOMMEND_IMAGING`, `CLINICAL_REVIEW`, `CONTINUE_SURVEILLANCE`). It does not make unauthorized clinical utility claims.

---

## 4. Empirical Verification & Acceptance Contract

All properties were empirically verified in `tests/acceptance_3b/test_k2_contract.py` (1,500 patients × 20 visits; 1,000 patients × 60 visits; 400 patients under exponential alternatives):

| Test / Scenario | Setup | Empirical Value | Target Contract Bound | Status |
|---|---|---|---|---|
| **Patient-Level Validity** (`gauss10`) | 1,500 pts, $\sigma=0.10$ | FAR = 0.0033 | $\le 0.0700$ | **PASSED** |
| **Patient-Level Validity** (`gauss12`) | 1,500 pts, $\sigma=0.12$ | FAR = 0.0153 | $\le 0.0700$ | **PASSED** |
| **Patient-Level Validity** (`heavy`) | 1,500 pts, Student-$t_5$ | FAR = 0.0087 | $\le 0.0700$ | **PASSED** |
| **Patient-Level Validity** (`ar1`) | 1,500 pts, $\rho=0.3, \sigma=0.10$ | FAR = 0.0213 | $\le 0.0700$ | **PASSED** |
| **Anytime Validity** | 1,000 pts, 60 serial visits | FAR = 0.0060 | $\le 0.0700$ | **PASSED** |
| **Missing Data Tolerance** | 800 pts, 30% missing (`None`) | FAR = 0.0037 | $\le 0.0700$ | **PASSED** |
| **Alert Latching** | Exponential growth stream | Latched = True | Never reverts | **PASSED** |
| **Power ($T_d = 90$d)** | 400 pts, onset at visit 6 | Sens = 100%, Med Delay = 117.8d | Sens $\ge 75\%$, Delay $\le 240$d | **PASSED** |
| **Power ($T_d = 60$d)** | 400 pts, onset at visit 6 | Sens = 100%, Med Delay = 96.2d | Sens $\ge 85\%$ | **PASSED** |

---

## 5. Limitations & Operating Scope
1. **Nadir Window Requirement:** Requires `burn_in = 3` initial post-adjuvant observations to establish the patient's individual running baseline.
2. **Analyte Scope:** Tuned for log-normal serum protein biomarkers (CA 15-3, CEA, CA 27-29) with assumed within-subject log standard deviation $\sigma_{\log} \approx 0.12$.
3. **Non-Diagnostic:** Detects evidence of non-stationarity and upward kinetic drift; clinical diagnosis requires imaging confirmation.
