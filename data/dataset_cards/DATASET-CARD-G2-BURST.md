# Dataset Card: Vigil Synthetic Cohort G2 (Shedding Bursts & Step Changes)

## 1. Dataset Summary
- **Dataset Name:** `cohort_g2_shedding_bursts`
- **Version:** `1.0.0`
- **Generator ID:** `g2_shedding_bursts`
- **Tier:** `T-S (Mechanistic Synthetic)`
- **Format:** Compressed CSV (`.csv.gz`) with accompanying JSON manifest and SHA-256 integrity checksums.
- **Intended Use:** Stress testing and benchmarking model resilience against non-smooth biomarker trajectories, acute necrotic core lysis spikes, and micro-vascular breach step-changes.
- **Out-of-Scope Use:** MUST NOT be used for direct clinical performance estimation.

## 2. Mechanistic Modeling Assumptions
- **Tumour Outgrowth Dynamics:** Episodic Poisson shot-noise burst events prior to clinical recurrence.
- **Biomarker Dynamics:** Discrete step changes representing vascular colonization combined with acute transient shedding spikes (washout within 14 days).
- **Target Organ Couplings:** Step-wise increases in organ-specific enzyme baselines upon metastatic seeding.
- **Anti-Leakage Protection:** Ground-truth burst counts, event dates, and step indices are isolated from feature representations.

## 3. Demographics & Clinical Priors
- Aligned with Nigerian clinical presentation series (E7): median age ~48.5 years, advanced stage presentation (75% Stage III/IV), and high triple-negative breast cancer prevalence (40%).

## 4. Empirical Performance
- Specificity: $\ge 99\%$ on disease-free trajectories.
- Sensitivity: $> 45\%$ on distant recurrences.
