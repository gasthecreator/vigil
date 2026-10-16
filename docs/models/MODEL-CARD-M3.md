# Model Card: Model M3 — Biomarker Plausibility Adjudicator

**Model Identifier:** `MODEL-M3-PLAUSIBILITY-ADJUDICATOR`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-16  
**Module Reference:** `packages/vigil-ml/vigil_ml/m3.py` (`vigil_ml.m3.adjudicate`, `vigil_ml.m3.rcv`)  
**Governing Documents:** `docs/MASTER_PLAN.md` §6.3, §14 WP4.1; `docs/ml/M3-M5-CONTRACT.md`; `docs/REALITY_RULES.md` RR7, RR14; `docs/EVIDENCE.md` E9  
**Acceptance Test Suite:** `tests/acceptance_p4/test_m3_contract.py` (all 7 contract tests passing)  
**Study Reference:** [`reports/ml/S7_PLAUSIBILITY/REPORT.md`](../../reports/ml/S7_PLAUSIBILITY/REPORT.md)  

---

## 1. Clinical Rationale & Intended Use

In routine serial oncology follow-up, unexpected biomarker spikes are frequently dismissed by clinicians as "lab error", delaying the detection of distant metastases until irreversible symptomatic progression. Conversely, genuine pre-analytical or analytical transcription errors (e.g. specimen mix-up, hemolysis, 10-fold decimal point slips) cause severe distress, unnecessary patient panic, and wasteful expensive imaging.

Model M3 functions as an intelligent, calibrated Bayesian adjudication barrier. When an unexpected measurement arrives, M3 evaluates whether the observation represents:
1. **True Disease Progression:** Genuine biological elevation exceeding biological noise.
2. **Gross Analytical or Collection Error:** Specimen misattribution, decimal shift, or assay failure.
3. **Biological & Analytical Variation:** Natural within-subject fluctuation around the patient's baseline.

### Clinical Safety Mandate: The Zero-Dismissal Policy
**Under no circumstances is an anomalous result ever labeled "dismissed" or discarded.** Anomalous results must either be:
- `explained`: Confirmed to lie within normal physiological baseline variation ($p_{\text{stable}} \ge 0.90$).
- `needs_repeat`: Requiring immediate re-draw confirmation before intervention ($p_{\text{error}} \ge 0.30$ or ambiguous).
- `escalate`: High confidence of disease recurrence requiring restaging ($p_{\text{real}} \ge 0.60$).

---

## 2. Mathematical Formulation & Generative Model

### Personalized Geometric Mean Baseline
A patient's physiological baseline level $L$ is established via the historical geometric mean:

$$\ln L = \frac{1}{n} \sum_{i=1}^n \ln(y_i)$$

where $y_i$ represents historical analyte concentrations at visits $i=1, \dots, n$.

### Variance Decomposition in Log-Space
Under small coefficient of variation approximations, the combined log-variance is:

$$\sigma_{\text{meas}}^2 = CV_a^2 + CV_i^2$$

Accounting for estimation error of the baseline mean ($\sigma_{\text{meas}}^2 / n$) and optional between-laboratory variance ($\sigma_{\text{lab}}^2 = \text{inter\_lab\_cv}^2$ if `lab_changed = True`):

$$\sigma^2 = \left(CV_a^2 + CV_i^2\right) \left(1 + \frac{1}{n}\right) + \left(\sigma_{\text{lab}}^2 \text{ if lab\_changed else } 0\right)$$

Let $\sigma = \sqrt{\sigma^2}$ and $\Delta \ln y = \ln(y / L) = \ln y - \ln L$.

### Closed-Form Likelihoods

1. **Stable Physiological State Likelihood:**
   $$\ln y \mid \text{stable} \sim \mathcal{N}\left(\ln L, \sigma^2\right) \implies P(\ln y \mid \text{stable}) = \frac{1}{\sqrt{2\pi}\sigma} \exp\left(-\frac{(\Delta \ln y)^2}{2\sigma^2}\right)$$

2. **True Progression Likelihood:**
   True progression is characterized by a persistent multiplicative rise factor $f \sim \text{LogUniform}(1.4, 3.0)$ convolved with Gaussian observation noise $\mathcal{N}(0, \sigma^2)$. The integrated density is:

   $$P(\ln y \mid \text{real}) = \frac{1}{\ln 3.0 - \ln 1.4} \left[ \Phi\left(\frac{\Delta \ln y - \ln 1.4}{\sigma}\right) - \Phi\left(\frac{\Delta \ln y - \ln 3.0}{\sigma}\right) \right]$$

   where $\Phi(z) = \frac{1}{2}\left[1 + \operatorname{erf}\left(\frac{z}{\sqrt{2}}\right)\right]$.

3. **Gross Laboratory Error Likelihood:**
   Gross errors comprise three equally weighted failure modes:
   - **Mode 0 (Specimen Mixup / Population Draw):** $\ln y \sim \mathcal{N}(\ln 18.0, 0.6^2 + \sigma_{\text{lab}}^2)$.
   - **Mode 1 (Decimal Shift Up $\times 10$):** $\Delta \ln y \sim \mathcal{N}(\ln 10.0, \sigma^2)$.
   - **Mode 2 (Decimal Shift Down $\div 10$):** $\Delta \ln y \sim \mathcal{N}(-\ln 10.0, \sigma^2)$.

   $$P(\ln y \mid \text{error}) = \frac{1}{3} \left[ \mathcal{N}\left(\ln y; \ln 18.0, 0.6^2 + \sigma_{\text{lab}}^2\right) + \mathcal{N}\left(\Delta \ln y; \ln 10.0, \sigma^2\right) + \mathcal{N}\left(\Delta \ln y; -\ln 10.0, \sigma^2\right) \right]$$

### Bayesian Posterior Inference
With prior probabilities $P(\text{real}) = 0.20$, $P(\text{error}) = 0.03$, and $P(\text{stable}) = 0.77$:

$$p_k = \frac{P(k) \cdot P(\ln y \mid k)}{\sum_{j \in \{\text{real}, \text{error}, \text{stable}\}} P(j) \cdot P(\ln y \mid j)}$$

---

## 3. Reference Change Value (RCV) Formulations (Evidence E9)

1. **Symmetrical Gaussian RCV ($95\%$ confidence, two-sided):**
   $$\text{RCV} = \sqrt{2} \cdot Z \cdot \sqrt{CV_a^2 + CV_i^2} \approx 2.77 \cdot \sqrt{CV_a^2 + CV_i^2}$$

2. **Asymmetrical Log-Normal RCV (preferred for $CV > 12\%$ or large shifts):**
   $$s = \sqrt{\ln(1 + CV_a^2) + \ln(1 + CV_i^2)}$$
   $$\text{RCV}_{\text{up}} = \exp\left(Z \sqrt{2} \cdot s\right) - 1, \quad \text{RCV}_{\text{down}} = \exp\left(-Z \sqrt{2} \cdot s\right) - 1$$

---

## 4. Biological Variation Parameter Evidence Status

All biological variation estimates are registered and audited per Evidence E9:

| Analyte | $CV_i$ (%) | $CV_g$ (%) | Index of Individuality ($II$) | Evidence Status | Literature Reference |
|---|---|---|---|---|---|
| **CA 15-3** | **6.1%** | 43.1% | 0.14 | **PRIMARY-VERIFIED** | Aarsand et al. 2021 (EuBIVAS), PMID 33964202 |
| **CEA** | **12.7%** | 55.4% | 0.23 | **PRIMARY-VERIFIED** | Aarsand et al. 2021 (EuBIVAS), PMID 33964202 |
| **ALP** | 6.5% | 25.8% | 0.25 | **SECONDARY** | EFLM 2019 / Ricós et al. 1999 update |
| **ALT** | 19.4% | 41.6% | 0.47 | **SECONDARY** | EFLM 2019 / Ricós et al. 1999 update |
| **AST** | 12.3% | 22.8% | 0.54 | **SECONDARY** | EFLM 2019 / Ricós et al. 1999 update |

> [!IMPORTANT]
> Because the Index of Individuality for CA 15-3 ($II = 0.14$) and CEA ($II = 0.23$) is well below $0.60$, population reference intervals (e.g. CA 15-3 $< 30\text{ U/mL}$) have very low sensitivity for patient-specific recurrence. Personalised geometric baseline monitoring is mandatory.

---

## 5. Quantitative Empirical Performance (Study S7 & Contract Suite)

Evaluated under `tests/acceptance_p4/test_m3_contract.py` ($N=3,000$ cases) and `reports/ml/S7_PLAUSIBILITY/REPORT.md`:

- **Discrimination:**
  - True Recurrence vs Stable Baseline: AUROC = **0.9961** [95% CI: 0.9937, 0.9977] (Target $\ge 0.85$).
  - Gross Error vs All Other Cases: AUROC = **0.9487** [95% CI: 0.9114, 0.9770] (Target $\ge 0.80$).
- **Calibration & Brier Skill:**
  - $p_{\text{real}}$ ECE = **0.0023** [95% CI: 0.0016, 0.0087] (Target $\le 0.06$).
  - $p_{\text{error}}$ ECE = **0.0025** [95% CI: 0.0022, 0.0067] (Target $\le 0.06$).
  - $p_{\text{real}}$ Brier score ratio vs prior baseline = **0.1121** (Target $\le 0.85$).
  - $p_{\text{error}}$ Brier score ratio vs prior baseline = **0.2353** (Target $\le 0.85$).
- **Lab-Change Sensitivity:**
  - A 1.35x elevation with `lab_changed = True` resulted in a strictly lower $p_{\text{real}}$ in **60 of 60 test cases (100%)**, preventing spurious alarms triggered by analyzer switches.
- **Zero-Dismissal Compliance:**
  - **100.00%** compliance across all runs.
