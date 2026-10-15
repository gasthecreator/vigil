# Model Card: Model K2 — Anytime-Valid Sequential Detection Engine

**Model Identifier:** `MODEL-K2-SEQUENTIAL-EPROCESS`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.0; `docs/ML_PROGRAM.md` §1 (H-B), §3.2, §6  
**Evaluation Status:** Evaluated across 5-Scenario Null Stress Suite (`reports/ml/S2_SEQUENTIAL/REPORT.md`)  

---

## 1. Model Overview and Intended Use
Model K2 solves the fundamental multi-testing hazard inherent in longitudinal oncology surveillance. In standard clinical practice, static threshold rules (e.g. CA 15-3 $\ge 30\text{ U/mL}$) are re-evaluated at every outpatient follow-up visit (up to 15–20 visits over 5 years). This serial repeated testing severely inflates the cumulative patient-level false alarm rate:

$$1 - (1 - \alpha)^K \gg \alpha$$

Model K2 formulates surveillance as an anytime-valid sequential hypothesis testing game using Nonnegative Test Supermartingales (e-processes) and Ville's Inequality. It mathematically guarantees that the cumulative probability of ever raising a false alarm over a patient's entire lifetime follow-up is bounded by the nominal budget $\alpha_{\text{pt}}$.

---

## 2. Mathematical Formulation & Martingale Mechanics
### Test Supermartingale & Ville's Inequality
Under the null hypothesis $H_0$ of clinical quiescence:
$$\mathbb{E}[E_t \mid \mathcal{F}_{t-1}] \le E_{t-1}, \quad E_0 = 1, \quad E_t \ge 0$$
By Ville's maximal inequality:
$$P_0\left(\exists t \ge 1 : E_t \ge \frac{1}{\alpha_{\text{pt}}}\right) \le \alpha_{\text{pt}}$$

### Mixture e-Process over Alternative Growth Rates
Because true metastatic doubling times vary widely (from aggressive 30-day doubling to indolent 360-day doubling), K2 integrates likelihood ratio increments over a pre-specified prior mixture grid $\mathcal{G} = \{g_1, \dots, g_M\}$:
$$E_t = E_{t-1} \sum_{m=1}^M w_m \exp\left(\Lambda_m(\Delta t_t, y_t, y_0)\right)$$

where $\Lambda_m$ is a Student-t log-likelihood ratio increment bounded against single-point outlier spikes ($\text{df}=4$), ensuring robust power under sustained exponential growth without sensitivity to isolated pre-analytical noise.

---

## 3. Calibrated Alert Tiers
- **Tier 1: Watch ($\alpha_{\text{pt}} = 0.20$, $E_t \ge 5$):** Early kinetic anomaly detected. Suggests scheduling an earlier follow-up visit (e.g. 45 days instead of 90 days) without alarming the patient or triggering invasive scans.
- **Tier 2: Review ($\alpha_{\text{pt}} = 0.05$, $E_t \ge 20$):** High confidence of subclinical progression. Triggers clinical oncology consultation and confirmatory serum repeat.
- **Tier 3: Urgent ($\alpha_{\text{pt}} = 0.01$, $E_t \ge 100$):** Extreme conviction of rapid metastatic growth. Triggers immediate diagnostic imaging protocol.

---

## 4. Evaluation and Stress Testing (Study S2)
1. **Cumulative Error Inflation of Static Rules:** Single static threshold rules exhibited a cumulative false alarm rate of $38.5\%$ over 15 visits under Gaussian null noise, completely violating the clinical 5% budget.
2. **Supermartingale Guarantee:** K2 maintained empirical patient-level false alarm rate $\le 4.2\%$ across all 5 pre-registered null stress scenarios:
   - Standard Gaussian biological variation ($\sigma = 2.2$).
   - Heavy-tailed Student-t noise ($\text{df} = 3, \sigma = 2.5$).
   - Inter-laboratory assay step change ($+4.5\text{ U/mL}$ at visit 8).
   - Transient hepatotoxicity spike ($+12\text{ U/mL}$ at visit 5).
   - Informative MNAR missingness (35% skipped quiescent tests).
3. **Detection Delay Advantage:** K2 achieved an Expected Detection Delay ($EDD$) of $42.3\text{ days}$ under true exponential recurrence, detecting disease $36.5\text{ days}$ earlier than static single-threshold rules.

---

## 5. Limitations & Operational Directives
- **Initial Baseline Sensitivity:** Accurate e-process initialization requires at least one reliable post-adjuvant nadir measurement $y_0$.
- **Not a Standalone Diagnostic:** E-values indicate deviations from patient-specific stationarity; definitive confirmation requires imaging and histopathology.
