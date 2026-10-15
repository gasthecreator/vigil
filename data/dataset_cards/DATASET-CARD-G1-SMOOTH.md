# Dataset Card: Vigil Synthetic Cohort G1 (Continuous Secretion Kinetics)

## 1. Dataset Summary
- **Dataset Name:** `cohort_g1_smooth_kinetics`
- **Version:** `1.0.0`
- **Generator ID:** `g1_smooth_kinetics`
- **Tier:** `T-S (Mechanistic Synthetic)`
- **Format:** Compressed CSV (`.csv.gz`) with accompanying JSON manifest and SHA-256 integrity checksums.
- **Intended Use:** Software correctness testing, pipeline integration, calibration target validation, and benchmarking of longitudinal continuous-time modeling families under smooth outgrowth assumptions.
- **Out-of-Scope Use:** MUST NOT be used for clinical validation, treatment efficacy evaluation, or uncalibrated diagnostic claims.

## 2. Mechanistic Modeling Assumptions
- **Tumour Outgrowth Dynamics:** Continuous exponential expansion transitioning to Gompertzian saturation at high cell masses ($B(t)$).
- **Secretion & Clearance Kinetics:** Circulating biomarker pools ($M_{\text{CA 15-3}}$, $M_{\text{CEA}}$) operate as filtered integrals of compartmental tumor burden with physiological elimination kinetics.
- **Organ Coupling:** Hepatocellular damage ($O_{\text{liver}}$) drives progressive elevations in ALT, AST, GGT, and Bilirubin; osteolytic bone remodeling ($O_{\text{bone}}$) elevates ALP and Calcium.
- **Treatment Effects:** Adjuvant chemotherapy active in the initial 180-day window induces transient myelosuppression (WBC/ANC/platelet nadir) and mild transient drug hepatotoxicity.
- **Verification Mechanism:** Imaging verification occurs probabilistically based on symptom severity, marker elevation, and scheduled visits.

## 3. Cohort Demographics & Clinical Priors (Nigerian Context E7, SEER E12)
- **Age:** Gaussian distribution $\mu = 48.5 \pm 9.5$ years (range 24–82 years).
- **Presentation Stage Mix:** Stage I (5%), Stage II (20%), Stage III (50%), Stage IV (25%).
- **Molecular Subtype Mix:** Triple-Negative Breast Cancer (TNBC, 40%), HR+/HER2- (42%), HER2+ (18%).
- **Metastatic Predilections:** Subtype-stratified according to SEER distant recurrence distributions (E12).

## 4. Calibration Targets (EVIDENCE E1)
- **Pre-clinical Lead Time:** $126 \pm 40$ days (4.2 ± 1.5 months) before clinical diagnosis.
- **Sensitivity at Recurrence:** ~54%–64% on distant recurrence.
- **Specificity:** $\ge 99\%$ on disease-free surveillance trajectories.

## 5. Ethical Considerations & Limitations
- This cohort contains purely in silico generated trajectories and zero Protected Health Information (PHI).
- Synthetic trajectories cannot capture unforeseen biological interactions, severe comorbid organ failures, or idiosyncratic laboratory artefacts not represented in the ODE model.
