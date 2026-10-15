# Model Card: Model K5 — Hierarchical Lab Harmonisation Engine

**Model Identifier:** `MODEL-K5-HARMONISATION-POOLING`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-G), §3.5, §6  
**Evaluation Status:** Evaluated under multi-site assay shift injection (`reports/ml/S5_HARMONISATION/REPORT.md`)  

---

## 1. Model Overview and Intended Use
In decentralized clinical oncology surveillance, patients frequently undergo routine blood testing across different hospital systems, regional laboratories, and reference platforms (e.g., Roche Cobas, Abbott Architect, Siemens Atellica). Systematic inter-assay calibration differences ($\pm 10\text{--}15\%$) or reagent lot shifts mimic subclinical tumor marker acceleration if unadjusted.

Model K5 provides a two-tier defense:
1. **Hierarchical Empirical Bayes Partial Pooling:** Estimates site-specific baseline offsets $\beta_\ell$ and scale factors $\sigma_\ell$ by shrinking site distributions toward global reference population priors.
2. **Online Analytical Changepoint Detector:** A CUSUM tracking chart operating on concurrent standardized residuals across all patients tested at the same facility, distinguishing systemic assay shifts from individual cancer recurrences.

---

## 2. Mathematical Formulation
### Empirical Bayes Shrinkage
For laboratory $\ell$ with $N_\ell$ observed test results $\{y_{\ell, 1}, \dots, y_{\ell, N_\ell}\}$ for analyte $k$:
$$\hat{\mu}_{\ell, k} = w_\ell \bar{y}_{\ell, k} + (1 - w_\ell) \mu_0$$
$$w_\ell = \frac{N_\ell}{N_\ell + \kappa_0}$$

where $\mu_0$ is the global reference population median and $\kappa_0$ is the shrinkage strength hyperparameter ($\kappa_0 = 15$).

### Observation Normalization
$$y^* = \frac{y_{\text{raw}} - \hat{\beta}_{\ell, k}}{\hat{\sigma}_{\ell, k}}$$

### Online CUSUM Residual Changepoint Detection
$$z_t = \frac{y_{\ell, t} - \mathbb{E}[y]}{\sigma_0}$$
$$C_t = \max\left(0, C_{t-1} + (z_t - 0.5)\right)$$

When $C_t > 5.0$, an automated system alert flags potential reagent lot recalibration or analyzer drift at laboratory $\ell$.

---

## 3. Evaluation and Stress Testing (Study S5)
- **False Alarm Inflation Under Shift:** When an analytical step shift of $+5.5\text{ U/mL}$ on CA 15-3 was injected into simulated Lab 5, an unharmonised model's false alarm rate inflated from $4.0\%$ to $28.0\%$.
- **Empirical Bayes Protection:** K5 hierarchical pooling correctly identified the site-specific offset, reducing the false alarm rate to $4.0\%$ (an $85.7\%$ relative reduction in spurious alerts).
- **Out-of-Distribution Calibration:** On completely held-out new clinical sites (zero training observations), K5 achieved a $34.2\%$ reduction in Brier score compared to unadjusted models.

---

## 4. Operational Directives
- **Mandatory Pre-Processing Gate:** All raw laboratory telemetry must pass through K5 before entering downstream scoring engines (K1, K3, K8).
- **Multi-Tenant Privacy:** K5 only aggregates summary statistics (means, standard deviations, sample counts) from participating sites, never patient-identifiable data.
