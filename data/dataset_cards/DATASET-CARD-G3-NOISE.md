# Dataset Card: Vigil Synthetic Cohort G3 (Heavy-Tailed Noise & Lab Offsets)

## 1. Dataset Summary
- **Dataset Name:** `cohort_g3_heavy_tailed_noise`
- **Version:** `1.0.0`
- **Generator ID:** `g3_heavy_tailed_noise`
- **Tier:** `T-S (Mechanistic Synthetic)`
- **Format:** Compressed CSV (`.csv.gz`) with accompanying JSON manifest and SHA-256 integrity checksums.
- **Intended Use:** Validating model robustness against real-world laboratory imperfections, heavy-tailed measurement errors, inter-facility analyzer calibration offsets, and pre-analytical artifact injections (haemolysis and dilution).
- **Out-of-Scope Use:** MUST NOT be used for direct clinical performance estimation.

## 2. Mechanistic Modeling Assumptions
- **Measurement Noise:** Heavy-tailed Student-t distribution ($\nu = 3$) capturing laboratory outliers and assay fluctuations.
- **Inter-Laboratory Offsets:** Each facility has systematic calibration offsets ($\pm 5\% - 12\%$) and scale factors per analyte (Task T8).
- **Pre-analytical Error Injections:**
  - *In vitro Haemolysis:* 4% probability per draw; selectively spikes AST ($2.5-4.5\times$) and LDH ($3.0-5.0\times$) due to erythrocyte lysis.
  - *Sample Dilution / Saline Contamination:* 2% probability per draw; uniformly reduces all serum analyte concentrations by $25-40\%$.
- **Informative Missingness (MNAR):** Missing visits and omitted high-cost tests driven by patient economic friction and transport barriers.

## 3. Demographics & Clinical Priors
- Grounded in Nigerian presentation priors (E7): median age ~48.5 years, advanced stage presentation (75% Stage III/IV), 40% TNBC subtype.
