# Vigil — Evidence Register

> Companion to `MASTER_PLAN.md`. Every external fact that the plan relies on is listed here with its **verification status**.
> 
> **Status values:**
> - `PRIMARY-VERIFIED`: Primary source read, DOI confirmed against Crossref, exact numbers quoted with page/table, and full dossier committed in `docs/evidence/{ID}.md`.
> - `SECONDARY`: Reported by a secondary summary or abstract; plausible; awaiting full-text dossier verification.
> - `BACKGROUND`: General domain knowledge, no specific citation retrieved yet.
> - `CONFLICTING`: Sources disagree on figures or findings.
> - `STALE`: Older than ~5 years or superseded; context only.
> - `BLOCKED`: Primary source is paywalled/unretrievable by executor without human subscription.
>
> **Enforcement:** Enforced in CI via `scripts/check_evidence.py`. No entry may be marked `PRIMARY-VERIFIED` without an existing `docs/evidence/{ID}.md` file and matching Crossref validation.

---

## Clinical and Biomarker Evidence

### E1 — Serial CA 15-3 and CEA in Follow-up: Lead Time, Sensitivity, and Guideline Stance — `PRIMARY-VERIFIED`
* **Dossier:** [`docs/evidence/E1.md`](evidence/E1.md)
* **Primary Sources:**
  1. Molina R, Zanon G, Filella X, Moreno F, Jo J, Daniels M, Latre ML, Pahisa J, Velasco M, Ballesta AM. "Use of serial carcinoembryonic antigen and CA 15.3 assays in detecting relapses in breast cancer patients." *Breast Cancer Res Treat*. 1995;36(1):41–48. doi:[10.1007/BF00690183](https://doi.org/10.1007/BF00690183). PMID:[7579505](https://pubmed.ncbi.nlm.nih.gov/7579505/).
  2. Duffy MJ. "Serum Tumor Markers in Breast Cancer: Are They of Clinical Value?" *Clin Chem*. 2006;52(3):345–351. doi:[10.1373/clinchem.2005.059832](https://doi.org/10.1373/clinchem.2005.059832). PMID:[16410341](https://pubmed.ncbi.nlm.nih.gov/16410341/).
  3. Khatcheressian JM, Wolff AC, Smith TJ, et al. "American Society of Clinical Oncology 2006 Update of the Breast Cancer Follow-Up and Management Guidelines in the Adjuvant Setting." *J Clin Oncol*. 2006;24(31):5091–5097. doi:[10.1200/JCO.2006.08.8575](https://doi.org/10.1200/JCO.2006.08.8575). PMID:[17033037](https://pubmed.ncbi.nlm.nih.gov/17033037/).
* **Verified Figures (Molina et al. 1995 cohort of 1,023 patients):**
  - Cohort: 1,023 primary breast cancer patients followed 1–10 years (mean 6.2 years); 246 patients developed metastases.
  - Pre-recurrence elevation lead time: 4.2 ± 2.3 months for CA 15-3 (elevated in 41% of recurrence cases prior to clinical diagnosis); 4.9 ± 2.2 months for CEA (elevated in 40%).
  - Sensitivity for distant metastasis (excluding locoregional recurrence): 54% for CA 15-3 alone; 64% for combined CEA and/or CA 15-3.
  - Specificity in disease-free (NED) patients: 99.0% for CEA (777 patients) and 99.0% for CA 15-3 (444 patients).
* **Guideline Stance (Khatcheressian 2006, Duffy 2006):** ASCO guidelines discourage routine serial tumor marker screening in unselected asymptomatic patients due to lack of overall survival benefit in 1990s randomized trials. Vigil positions longitudinal surveillance not as an unselected screening tool, but as an individualized anomaly detection and triage engine to prioritize diagnostic restaging in resource-constrained environments.
* **Used by:** MASTER_PLAN §2, §6.2, §6.13, simulator calibration targets (tuned to reproduce Molina 1995 figures).

### E2 — Marker Velocity Thresholds — `SECONDARY`
* Reported sensitivity 94.0%, specificity 73.1% in a matched case-control design; matched case-control designs overstate real-world prospective performance.
* Source: https://doaj.org/article/fcb8387deedd4cb2acf24f1e6f3ae001 (*Breast*, Aug 2020). Primary paper to be retrieved and appraised.
* **Used by:** Velocity-rule baseline (§6.2).

### E3 — ctDNA / Molecular Residual Disease Lead Times — `SECONDARY`
* Reported median lead times to clinical relapse: 10.7 months (95% CI 8.1–19.1; n=101, tumor-informed); 11.7 months (PCM assay, 2024); 10.5 months (range 0–38; Signatera, 156 patients); 6.1 months in TNBC cTRAK-TN (n=141).
* Sources: PMC11402396, PMC10870111, PMC6681568.
* **Limitations:** Assays and schedules differ; many retrospective; high cost and lack of availability in low-resource settings.
* **Used by:** MASTER_PLAN §2, §6.13.

### E9 — Biological Variation, Analytical Specifications, and RCV — `PRIMARY-VERIFIED`
* **Dossier:** [`docs/evidence/E9.md`](evidence/E9.md)
* **Primary Sources:**
  1. Aarsand AK, Díaz-Garrote S, Corte Z, et al. "Within- and between-subject biological variation data for tumor markers based on the European Biological Variation Study." *Clin Chem Lab Med*. 2021;60(2):238–248. doi:[10.1515/cclm-2021-0283](https://doi.org/10.1515/cclm-2021-0283). PMID:[33964202](https://pubmed.ncbi.nlm.nih.gov/33964202/).
  2. Ricós C, Alvarez V, Cava F, et al. "Current databases on biological variation: pros, cons and progress." *Scand J Clin Lab Invest*. 1999;59(7):491–500. doi:[10.1080/00365519950185229](https://doi.org/10.1080/00365519950185229). PMID:[10667686](https://pubmed.ncbi.nlm.nih.gov/10667686/).
  3. Fraser CG. *Biological Variation: From Principles to Practice*. Washington, DC: AACC Press; 2001. ISBN: 978-1890883492.
* **Verified Formulations & Parameters:**
  - Reference Change Value: $\text{RCV} = 2^{1/2} \times Z \times \sqrt{CV_a^2 + CV_i^2}$.
  - Index of Individuality: $\text{II} = CV_i / CV_g$. For CA 15-3, $CV_i = 6.1\%$, $CV_g = 43.1\%$, yielding $\text{II} = 0.14$. Because $\text{II} < 0.6$, conventional population reference intervals have low sensitivity for detecting personal pathological changes.
  - CEA: $CV_i = 12.7\%$, $CV_g = 55.4\%$, $\text{II} = 0.23$.
* **Used by:** Analyte registry (`packages/vigil-core/vigil_core/analytes.py`), Plausibility Adjudicator (Module M3).

### E12 — Metastatic Site Tropism by Subtype — `PRIMARY-VERIFIED`
* **Dossier:** [`docs/evidence/E12.md`](evidence/E12.md)
* **Primary Source:**
  1. Wu Q, Li J, Zhu S, et al. "Breast cancer subtypes predict the preferential site of distant metastases: a SEER based study." *Oncotarget*. 2017;8(17):27990–27996. doi:[10.18632/oncotarget.15856](https://doi.org/10.18632/oncotarget.15856). PMID:[28427196](https://pubmed.ncbi.nlm.nih.gov/28427196/).
* **Verified Figures (SEER 2010–2013 Cohort n=243,896):**
  - Distant metastatic site breakdown among documented sites:
    - Bone metastasis: 8,848 cases (50.7% of metastatic events; predominant across all subtypes, highest in HR+/HER2-).
    - Lung metastasis: 4,167 cases (23.9%).
    - Liver metastasis: 3,434 cases (19.7%; significantly elevated in HER2+ subtypes).
    - Brain metastasis: 1,000 cases (5.7%; highest in HR-/HER2+ [OR = 1.978] and Triple Negative).
* **Used by:** Model M1 baseline organ susceptibility priors, `vigil-sim` latent seeding probabilities.

---

## Context: Nigeria

### E6 — Radiotherapy Capacity in Nigeria — `SECONDARY` / `STALE`
* ~200M population, estimated shortfall of ~280 LINACs by IAEA benchmarks; high out-of-pocket costs and machine downtime. Current national facility assessment pending hospital partnership data.
* Sources: PMC7456314; local press reports.
* **Used by:** Treatment delay and harm modeling (Module M7).

### E7 — Nigerian Breast Cancer Presentation, Staging, and Subtypes — `PRIMARY-VERIFIED`
* **Dossier:** [`docs/evidence/E7.md`](evidence/E7.md)
* **Primary Sources:**
  1. Jedy-Agba E, McCormack V, Adebamowo C, dos-Santos-Silva I. "Stage at diagnosis of breast cancer in sub-Saharan Africa: a systematic review and meta-analysis." *Lancet Glob Health*. 2016;4(12):e923–e935. doi:[10.1016/S2214-109X(16)30259-5](https://doi.org/10.1016/S2214-109X(16)30259-5). PMID:[27855871](https://pubmed.ncbi.nlm.nih.gov/27855871/).
  2. Huo D, Ikpatt OF, Khramtsov A, et al. "Population differences in breast cancer: survey in indigenous African women reveals over-representation of triple-negative breast cancer." *J Clin Oncol*. 2009;27(27):4515–4521. doi:[10.1200/JCO.2008.19.6873](https://doi.org/10.1200/JCO.2008.19.6873). PMID:[19704069](https://pubmed.ncbi.nlm.nih.gov/19704069/).
* **Verified Figures:**
  - Advanced stage presentation: In sub-Saharan Africa, median percentage presenting at Stage III/IV is 74.7% (Jedy-Agba 2016, 83 studies, 26,788 patients).
  - Young age at diagnosis: Mean age at diagnosis is 44.8 ± 11.8 years in Nigerian/Senegalese cohort (Huo 2009), 12–15 years younger than North American cohorts.
  - Molecular subtype breakdown (Huo 2009 indigenous cohort, n=378): Triple Negative represents 55% (derived sum: 27% basal-like + 28% unclassified); Luminal A 27%; Luminal B 2%; HER2+/ER- 15%.
* **Used by:** `vigil-sim` demographic and biological priors, clinical study protocol (`docs/clinical/PARTNERSHIP/STUDY-PROTOCOL.md`).

### E14 — Nigeria Data Protection Act 2023 — `PRIMARY-VERIFIED`
* **Dossier:** [`docs/evidence/E14.md`](evidence/E14.md)
* **Primary Source:**
  1. Nigeria Data Protection Act, 2023. Act No. 34 of 2023, Federal Republic of Nigeria Official Gazette No. 119, Vol. 110, Acts No. 16, Abuja, 14th June 2023. Official NDPC Gazette: [https://ndpc.gov.ng/Files/NDPA2023.pdf](https://ndpc.gov.ng/Files/NDPA2023.pdf).
* **Key Verified Provisions:**
  - Section 30: Health data is sensitive personal data; processing permitted under Section 30(1)(i) for public health, scientific research, and archiving purposes.
  - Section 28: Mandatory Data Protection Impact Assessment (DPIA) for high-risk or special category health processing.
  - Section 41–43: Cross-border transfer restrictions and data localization requirements.
* **Used by:** Data Protection Impact Assessment (`docs/clinical/PARTNERSHIP/DPIA.md`), Data Use Agreement (`docs/clinical/PARTNERSHIP/DUA-TEMPLATE.md`).

---

## Treatment Delay and Harm

### E8 — Radiotherapy Delay and Recurrence — `SECONDARY`
* Meta-analysis (Mackillop et al., *Clin Oncol* 2016, ~79,600 patients): Relative risk of local recurrence 1.08 per month of delay (95% CI 1.02–1.14) after breast-conserving surgery.
* Primary text to be retrieved for post-mastectomy and TNBC-specific cohorts.
* **Used by:** Harm model (Module M7).

---

## Communication and Behavioral Interventions

### E10 — SMS Reminders for Clinical Follow-up in Sub-Saharan Africa — `SECONDARY`
* Kenyan RCT in cervical screening re-attendance showed OR 8.02 (95% CI 4.69–13.73) with SMS reminders. No oncology-specific WhatsApp RCT found.
* Primary sources: PMC5698928.
* **Used by:** Follow-up Guardian (Module M6).

---

## Machine Learning & Statistical Methods

### E11 — Irregular Clinical Time-Series Modeling — `SECONDARY`
* GRU-D, GRU-ODE-Bayes, Neural CDE, and GRU with exponential basis functions (GRUwE, Joshi & Hauskrecht, TMLR 2026).
* Primary papers to be retrieved for empirical benchmark comparison.
* **Used by:** `docs/ML_PROGRAM.md` §3.4.

### E16 — Adaptive Conformal Prediction — `SECONDARY`
* Gibbs & Candès (NeurIPS 2021) on adaptive conformal inference for time series.
* **Used by:** Uncertainty and abstention (Module M8).

### E15 — AI Health Reporting Guidelines — `SECONDARY`
* TRIPOD+AI (2024), PROBAST+AI, and DECIDE-AI (BMJ 2022).
* **Used by:** Evaluation reporting standards.

---

## Data Repositories

### E13 — Public Registry and Trial Data Availability — `SECONDARY`
* SEER (NCI): Demographics, stage, subtype, metastatic sites, survival; no serial laboratory draws.
* METABRIC / TCGA-BRCA: Genomic profiles, clinical stages, recurrence dates (days from diagnosis); no serial outpatient lab series.
* Project Data Sphere: Comparator arms from prospective trials; lab test frequency is protocol-dependent.
* MIMIC-IV: Dense longitudinal inpatient series; ICU selection bias documented.
* **Used by:** `docs/data/ACCESS.md`.

---

## Regulation and Governance

### E17 — FDA Clinical Decision Support Software Guidance — `SECONDARY`
* FDA Final Guidance (Jan 2026) regarding Non-Device CDS criteria.
* **Used by:** Regulatory classification and claims policy.

### E18 — Nigerian Medical Device & Health AI Regulation — `SECONDARY`
* NAFDAC regulatory framework and National Health Research Ethics Committee (NHREC) guidelines.
* **Used by:** Ethics application drafting (`docs/clinical/PARTNERSHIP/ETHICS-APPLICATION.md`).

### E19 — WHO AI for Health Ethics Guidance — `SECONDARY`
* WHO 2024 guidance on multimodal foundation models and clinical decision support.
* **Used by:** System safety and hazard log.
