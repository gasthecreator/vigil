# Model Card: Model M1 — Bayesian Organ Susceptibility Model

**Model Identifier:** `MODEL-M1-ORGAN-SUSCEPTIBILITY`  
**Model Version:** 1.0.0-alpha  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP2.3; `docs/ML_PROGRAM.md` §9; `docs/evidence/E14.md`  
**Evidence Level:** `[PRIMARY-VERIFIED]` (Registry SEER proportions from Wu et al. 2017; Subtype distribution from Huo et al. 2009)  

---

## 1. Model Overview and Intended Use
Model M1 estimates the conditional probability distribution of initial distant metastatic recurrence across the four canonical target organ compartments:
- **Bone** (osteolytic and osteoblastic metastases)
- **Liver** (hepatic parenchymal metastasis)
- **Lung** (pleuropulmonary metastatic disease)
- **Brain** (central nervous system metastasis)

### Intended Use
- Provides baseline physiological priors that weight multi-analyte surveillance signals (e.g. upweighting alkaline phosphatase when bone risk is elevated, or ALT/AST/bilirubin when hepatic risk is elevated).
- Informs Model M4 (Second-Tier Imaging Recommender) regarding modality choice (e.g. bone scintigraphy vs. abdominal ultrasound).
- **Prohibited Use:** Model M1 MUST NOT be used to deny diagnostic workup, restrict patient follow-up, or stage primary breast cancer without histopathological verification.

---

## 2. Mathematical Formulation
Model M1 employs a hierarchical Bayesian Dirichlet-Multinomial parameterization:
$$y_i \sim \text{Multinomial}(n_i, \theta_s)$$
$$\theta_s \sim \text{Dirichlet}(\alpha_s)$$

where $s \in \{\text{TNBC}, \text{HR}^+\text{HER2}^-, \text{HER2}^+\}$ is the patient's primary molecular subtype, and $\alpha_s$ represents the Dirichlet concentration hyper-parameter vector informed by large-scale empirical population evidence.

### Evidence-Derived Prior Counts
Derived from SEER analysis by Wu et al. 2017 (n=243,896; DOI: `10.1186/s12885-017-3824-z`, `docs/evidence/E14.md`):
- **HR+/HER2- (Luminal):** Bone 65.4%, Liver 14.2%, Lung 15.3%, Brain 5.1%
- **HER2+ (Enriched):** Bone 44.8%, Liver 28.5%, Lung 19.2%, Brain 7.5%
- **TNBC (Basal-like):** Bone 38.6%, Liver 21.4%, Lung 30.5%, Brain 9.5%

---

## 3. Performance and Calibration
- **Bayesian Credible Intervals:** Evaluates complete posterior parameter distributions with 95% equal-tailed credible intervals.
- **Shrinkage Regularization:** When clinical stage or subtype data are partially missing, the model shrinks estimates toward empirical population base rates rather than returning arbitrary defaults.
- **Inference Latency:** Closed-form Dirichlet posterior mode and covariance calculation executes in $< 0.1$ ms on CPU, well within the 100 ms clinical workstation budget.

---

## 4. Limitations and Ethical Considerations
1. **Subtype Misclassification:** In low-resource settings, immunohistochemistry (IHC) testing may be delayed, incomplete, or absent. Model M1 provides uninformative diffuse Dirichlet fallback modes for uncharacterized tumors.
2. **Synthetic Validation:** Current integration testing is performed on synthetic cohorts (Tiers G1–G3). Clinical utility validation requires retrospective partner hospital audits (T-R tier).
3. **Multi-Site Metastases:** Model M1 parameterizes the *initial* site of clinically apparent distant recurrence; subsequent oligometastatic cascades are modeled separately in Phase 3.
