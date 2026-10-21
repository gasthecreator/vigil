# Model Card: Model K2 — Sequential Detection Research Prototype

**Model Identifier:** `MODEL-K2-SEQUENTIAL-DETECTOR`
**Model Version:** 1.1.0-alpha
**Date:** 2026-10-16
**Module Reference:** `packages/vigil-ml/vigil_ml/k2.py` (`vigil_ml.k2.SequentialDetector`)
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-B), §3.2, §6; `docs/ml/K2-K8-CONTRACT.md`
**Acceptance Test Suite:** `tests/acceptance_3b/test_k2_contract.py` (empirical contract checks; not a proof of validity)
**Study Reference:** [`reports/ml/S2_SEQUENTIAL/REPORT.md`](../../reports/ml/S2_SEQUENTIAL/REPORT.md) (**retracted**)

---

## 1. Model Overview and Intended Use
K2 is research code for scoring longitudinal marker sequences. Its patient-level false-alarm guarantee has **not been established**, and its scores must not be interpreted as calibrated probabilities, diagnoses, or clinical action thresholds. Study S2 is retracted pending a corrected protocol and independent replication.

Repeated fixed-threshold testing can inflate false alarms under suitable assumptions; this does not validate K2. The formula below is illustrative only:

$$1 - (1 - \alpha)^K \gg \alpha$$

For example, with $K=20$ visits at nominal $\alpha=0.05$, the unadjusted false alarm rate reaches $1 - 0.95^{20} = 64.2\%$.

The code accumulates scores using an exponential-mixture form. Ville's inequality would apply only if each component were a nonnegative supermartingale under the null. That requires, at minimum, conditionally centered standardized residuals with a valid conditional sub-Gaussian scale bound. The implementation's recursive residual is not shown to be conditionally centered given prior observations, and its scale estimate from a finite synthetic cohort is not a proven upper bound. Therefore the formula does not establish an e-process guarantee for this implementation. The formal condition for Ville's inequality is that the process is a nonnegative supermartingale; see [Howard et al., *Time-uniform Chernoff bounds via nonnegative supermartingales*](https://projecteuclid.org/journals/probability-surveys/volume-17/issue-none/Time-uniform-Chernoff-bounds-via-nonnegative-supermartingales/10.1214/18-PS321).

---

## 2. Mathematical Formulation & Martingale Mechanics

### Recursive Standardisation Against Running Baseline
A known pitfall of serial surveillance is that estimating a patient's baseline from initial visits leaves a persistent bias that accumulates over long monitoring and breaks validity. To prevent this, K2 uses the Brown-Durbin-Evans (1975) recursive prediction residual against the running baseline:

$$w_t = \sqrt{\frac{n}{n + 1}} \left(y_t - \bar{y}_{1:n}\right)$$

where $y_t = \log(\text{marker}_t)$, $n$ is the count of previous observations ($n \ge \text{burn\_in} = 3$), and $\bar{y}_{1:n} = \frac{1}{n} \sum_{i=1}^n y_i$. Under an i.i.d. fixed-mean model this residual is unconditionally centered, but its conditional mean given prior observations is generally not zero. That distinction prevents treating the following score as a proven supermartingale.

The standardized increment is:
$$z_t = \frac{w_t}{\sigma_{\log}}$$

### Exponential-mixture score (validity not established)
For each candidate growth rate $\lambda \in \{0.3, 0.5, 0.7, 1.0\}$, the implementation accumulates:

$$M_t(\lambda) = \exp\left(\sum_{s=1}^t \left(\lambda z_s - \frac{\lambda^2}{2}\right)\right)$$

The implementation computes a uniform mixture score over the candidate growth rates:

$$E_t = \frac{1}{|\mathcal{G}|} \sum_{\lambda \in \mathcal{G}} M_t(\lambda)$$

In logarithmic space:
$$\log E_t = \operatorname{logsumexp}\left(\log \mathbf{w} + \log \mathbf{M}_t\right)$$

### Thresholds & Latching
The implementation compares the accumulated score with thresholds and latches alerts. These thresholds do **not** currently carry a proven patient-level false-alarm interpretation. The following inequality is a property of valid nonnegative supermartingales, not an established guarantee for this implementation:

$$P_0\left(\exists t \ge 1 : E_t \ge \frac{1}{\alpha_{\text{pt}}}\right) \le \alpha_{\text{pt}}$$

When $\log E_t \ge \log(1 / \alpha_{\text{pt}})$, the detector raises a latched software alert. Latching is an implementation behavior, not evidence of clinical validity.

The unchanged historical defaults (`alpha_pt`, `sigma_log`, burn-in, growth grid, and software-tier cutoffs) are stored in [`k2_research_config_v1.json`](../../packages/vigil-ml/vigil_ml/models/k2_research_config_v1.json). The file identifies them as unvalidated research defaults. API provenance records both the source-file hash and hash of effective settings. The fixed scale has no per-analyte calibration evidence.

---

## 3. Alert Tiers & Score Integration

The score is grouped into software tiers at the following numerical thresholds. These labels do not currently represent calibrated error budgets or clinical action guidance:
- Tier 0: None ($E_t < 5$).
- Tier 1: Watch ($\log E_t \ge \ln(5) \approx 1.609$).
- Tier 2: Review ($\log E_t \ge \ln(20) \approx 2.996$).
- Tier 3: Urgent ($\log E_t \ge \ln(100) \approx 4.605$).

### Landmark Risk Score Integration
`SequentialDetector.integrate_with_risk_score(score, imaging_threshold)` is disabled and raises for valid-looking inputs. The former implementation could return `RECOMMEND_IMAGING` from unvalidated scores and a caller-provided threshold; no clinical action threshold has been validated. No product call sites were found.

---

## 4. Empirical Verification & Acceptance Contract

The acceptance suite reports the following empirical rates under its specified synthetic scenarios (1,500 patients × 20 visits; 1,000 patients × 60 visits; 400 patients under exponential alternatives). These finite simulations do not prove the required conditional supermartingale property:

| Test / Scenario | Setup | Empirical Value | Target Contract Bound | Status |
|---|---|---|---|---|
| **Empirical FAR** (`gauss10`) | 1,500 pts, $\sigma=0.10$ | FAR = 0.0033 | $≤ 0.0700$ | **EMPIRICAL PASS** |
| **Empirical FAR** (`gauss12`) | 1,500 pts, $\sigma=0.12$ | FAR = 0.0153 | $≤ 0.0700$ | **EMPIRICAL PASS** |
| **Empirical FAR** (`heavy`) | 1,500 pts, Student-$t_5$ | FAR = 0.0087 | $≤ 0.0700$ | **EMPIRICAL PASS** |
| **Empirical FAR** (`ar1`) | 1,500 pts, $\rho=0.3, \sigma=0.10$ | FAR = 0.0213 | $≤ 0.0700$ | **EMPIRICAL PASS** |
| **Empirical FAR** | 1,000 pts, 60 serial visits | FAR = 0.0060 | $≤ 0.0700$ | **EMPIRICAL PASS** |
| **Missing Data Tolerance** | 800 pts, 30% missing (`None`) | FAR = 0.0037 | $≤ 0.0700$ | **EMPIRICAL PASS** |
| **Alert Latching** | Exponential growth stream | Latched = True | Never reverts | **OBSERVED** |
| **Power ($T_d = 90$d)** | 400 pts, onset at visit 6 | Sens = 100%, Med Delay = 117.8d | Sens $\ge 75\%$, Delay $\le 240$d | **EMPIRICAL** |
| **Power ($T_d = 60$d)** | 400 pts, onset at visit 6 | Sens = 100%, Med Delay = 96.2d | Sens $\ge 85\%$ | **EMPIRICAL** |

---

## 5. Limitations & Operating Scope
1. The recursive residual's conditional null distribution has not been established.
2. The supplied $\sigma_{\log}$ estimate is not shown to upper-bound conditional variation.
3. The acceptance stress scenarios cover a finite set of synthetic distributions only.
4. The feature is research-only; no clinical decision rule or deployment guarantee is supported.
5. The API keeps separate histories by analyte and replays same-analyte observations in specimen-time order. This prevents cross-marker scale contamination and handles late-arriving specimens; it does not establish that one fixed `sigma_log` or score configuration is suitable for every analyte.
6. The legacy clipped prototype and benchmark in `vigil_ml.sequential_k2` are retired; their compatibility imports raise on construction. The S2 evidence remains retracted.
