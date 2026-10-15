# Study S5 Pre-Registration: Multi-Site Hierarchical Pooling & Lab Harmonisation

**Study ID:** S5_HARMONISATION  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-G), §3.5, §6  

---

## 1. Study Objective and Research Question
Tumor marker assays (e.g. CA 15-3, CEA) and automated clinical chemistry analyzers exhibit substantial inter-laboratory and inter-method variability. Without analytical harmonisation, a shift in assay calibration or batch differences between hospitals mimics metastatic disease progression.

**Core Question:** Does hierarchical Bayesian partial pooling across testing facilities and real-time analytical changepoint detection prevent spurious false alarms under injected laboratory shifts, while improving calibration on held-out new sites?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Shift Sensitivity of Unharmonised Models):** An unharmonised threshold or survival model evaluated on data from a laboratory with an assay step change of $+5.0\text{ U/mL}$ will experience a $> 3\times$ inflation in false alarm rate.
2. **H2 (Empirical Bayes Protection):** K5 hierarchical pooling will estimate site-specific random effects, reducing false alarms under lab shifts by $> 60\%$ while maintaining sensitivity.
3. **H3 (Changepoint Detection):** Online CUSUM tracking of concurrent standardized residuals from the same testing facility will identify assay batch shifts within $\le 10$ patient visits, triggering automated lab recalibration.

---

## 3. Evaluated Models
- **M-Unharmonised:** Global model applied directly to raw laboratory values without site covariates.
- **M-FixedEffects:** Model including unpooled one-hot categorical site indicators.
- **K5-Hierarchical:** Hierarchical Bayesian model with partial pooling of offsets and scales toward global reference priors, coupled with online residual changepoint tracking.

---

## 4. Evaluated Cohort & Multi-Site Setup
- $N = 1,500$ synthetic patients distributed across 6 participating hospital laboratories:
  - Labs 1–4: In-distribution reference clinical sites.
  - Lab 5: Site with sustained analytical offset ($+5.5\text{ U/mL}$ on CA 15-3).
  - Lab 6: Completely held-out new site (zero training samples) to evaluate few-shot transfer.

---

## 5. Primary and Secondary Endpoints
1. **Primary Metric:** False alarm rate under injected assay shift ($\text{FAR}_{\text{shift}}$).
2. **Secondary Metrics:**
   - Out-of-distribution Brier score on held-out Lab 6.
   - Mean Absolute Error (MAE) of recovered laboratory offsets $\hat{\beta}_\ell$ vs true ground-truth offsets.
   - Run length to changepoint detection.

---

## 6. Pre-Registered Decision Criteria
Per `docs/ML_PROGRAM.md` §6:
- If hierarchical pooling fails to improve calibration (Brier score reduction $\ge 15\%$) on held-out new sites compared to simple fixed offsets, fall back to simple per-lab static offsets.
