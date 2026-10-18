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

### E9 — Biological Variation, Analytical Specifications, and RCV — `SECONDARY`
* **Dossier:** [`docs/evidence/E9.md`](evidence/E9.md)
* **Primary Sources:**
  1. Aarsand AK, Díaz-Garrote S, Corte Z, et al. "Within- and between-subject biological variation data for tumor markers based on the European Biological Variation Study." *Clin Chem Lab Med*. 2021;60(2):238–248. doi:[10.1515/cclm-2021-0283](https://doi.org/10.1515/cclm-2021-0283). PMID:[33964202](https://pubmed.ncbi.nlm.nih.gov/33964202/).
  2. Ricós C, Alvarez V, Cava F, et al. "Current databases on biological variation: pros, cons and progress." *Scand J Clin Lab Invest*. 1999;59(7):491–500. doi:[10.1080/00365519950185229](https://doi.org/10.1080/00365519950185229). PMID:[10667686](https://pubmed.ncbi.nlm.nih.gov/10667686/).
  3. Fraser CG. *Biological Variation: From Principles to Practice*. Washington, DC: AACC Press; 2001. ISBN: 978-1890883492.
  4. Westgard QC Desirable Biological Variation Database specifications (Ricós et al.). URL: https://www.westgard.com/biodatabase1.htm. Saved Excerpt: [`docs/evidence/excerpts/E9_westgard_ricos_biodatabase.md`](evidence/excerpts/E9_westgard_ricos_biodatabase.md).
* **Verified Formulations & Parameters:**
  - Reference Change Value: $\text{RCV} = 2^{1/2} \times Z \times \sqrt{CV_a^2 + CV_i^2}$.
  - Index of Individuality: $\text{II} = CV_i / CV_g$. For CA 15-3, $CV_i = 6.1\%$, $CV_g = 62.9\%$, yielding $\text{II} = 0.10$. Because $\text{II} < 0.6$, conventional population reference intervals have low sensitivity for detecting personal pathological changes.
  - CEA: $CV_i = 12.7\%$, $CV_g = 55.6\%$, $\text{II} = 0.23$.
* **Used by:** Analyte registry (`packages/vigil-core/vigil_core/analytes.py`), Plausibility Adjudicator (Module M3).

### E12 — Metastatic Site Tropism by Subtype — `SECONDARY` (downgraded by overseer 2026-10-17: saved 'verbatim' excerpt contains numbers absent from the retrievable source; see scripts/audit_excerpts.py and docs/progress/VERDICT-P5A.md)
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

### E20 — Imaging Sensitivity for Liver Metastases (ultrasound, CT, MRI) — `SECONDARY` (abstract-level; numbers machine-verified against the PubMed abstract by `scripts/audit_excerpts.py`)
* **Primary source:** Kinkel K, Lu Y, Both M, Warren RS, Thoeni RF. "Detection of hepatic metastases from cancers of the gastrointestinal tract by using noninvasive imaging methods (US, CT, MR imaging, PET): a meta-analysis." *Radiology*. 2002;224(3):748-756. doi:[10.1148/radiol.2243011362](https://doi.org/10.1148/radiol.2243011362). PMID:[12202709](https://pubmed.ncbi.nlm.nih.gov/12202709/).
* **Excerpt:** [`docs/evidence/excerpts/E20_kinkel_2002_liver_imaging.md`](evidence/excerpts/E20_kinkel_2002_liver_imaging.md).
* **Figures (data sets with specificity above 85 percent):** weighted sensitivity 55 percent (95% CI 41 to 68) for ultrasound, 72 percent (63 to 80) for CT, 76 percent (57 to 91) for MRI, 90 percent (80 to 97) for FDG PET.
* **Limits:** colorectal, gastric and esophageal primaries, not breast; publication date 2002 (older technology); sensitivity is reported within a specificity stratum, not as a pooled specificity; full text not read.
* **Used by:** M4 test ladder (liver rows).

### E21 — Imaging Accuracy for Bone Metastases (bone scintigraphy, MRI, CT, PET) — `SECONDARY` (abstract-level; numbers machine-verified against the PubMed abstracts)
* **Primary sources:**
  1. Yang HL, Liu T, Wang XM, Xu Y, Deng SM. "Diagnosis of bone metastases: a meta-analysis comparing 18FDG PET, CT, MRI and bone scintigraphy." *Eur Radiol*. 2011;21(12):2604-2617. doi:[10.1007/s00330-011-2221-4](https://doi.org/10.1007/s00330-011-2221-4). PMID:[21887484](https://pubmed.ncbi.nlm.nih.gov/21887484/). Excerpt: [`E21a`](evidence/excerpts/E21a_yang_2011_bone_imaging.md).
  2. Liu T, Cheng T, Xu W, Yan WL, Liu J, Yang HL. "A meta-analysis of 18FDG-PET, MRI and bone scintigraphy for diagnosis of bone metastases in patients with breast cancer." *Skeletal Radiol*. 2011;40(5):523-531. doi:[10.1007/s00256-010-0963-8](https://doi.org/10.1007/s00256-010-0963-8). PMID:[20495798](https://pubmed.ncbi.nlm.nih.gov/20495798/). Excerpt: [`E21b`](evidence/excerpts/E21b_liu_2011_bone_imaging_breast.md).
* **Figures (per patient, pooled point estimates; no confidence intervals in the abstracts):** all cancers (source 1) sensitivity 89.7 percent PET, 72.9 CT, 90.6 MRI, 86.0 bone scintigraphy; specificity 96.8, 94.8, 95.4, 81.4. Breast cancer (source 2) sensitivity 83.3 PET, 97.1 MRI, 87.0 bone scintigraphy; specificity 94.5, 97.0, 88.1; CT not analysed.
* **Limits:** abstract-level; both papers share an author group and overlapping literature (they are not independent); both searched to January 2010.
* **Not sourced (excluded by M4):** plain radiograph and alkaline-phosphatase or calcium trend for bone metastases: no accuracy source was retrieved.
* **Used by:** M4 test ladder (bone rows).

### E22 — Chest Radiograph versus Chest CT for Pulmonary Metastases — `SECONDARY` (single study, weak; figures NOT machine-verified)
* **Source:** Mahajan A, Shukla S, Nandi D, et al. "CT-Based Screening for Pulmonary Metastases in Head and Neck Squamous Cell Cancers: Diagnostic Accuracy and Cost Comparison with PET-CECT." *Indian J Surg Oncol*. 2023;14(4):881-889. doi:[10.1007/s13193-023-01783-z](https://doi.org/10.1007/s13193-023-01783-z). PMID:[38187855](https://pubmed.ncbi.nlm.nih.gov/38187855/). Excerpt and caveats: [`docs/evidence/excerpts/E22_mahajan_2023_chest_xray_ct.md`](evidence/excerpts/E22_mahajan_2023_chest_xray_ct.md).
* **Figures (read from the PMC full text, unverified by the audit script):** chest radiograph sensitivity 49 percent, specificity 88 percent (89 in the Discussion); chest CT sensitivity 97.3 percent, specificity 97.2 percent; the authors also cite a literature range of 20 to 50 percent sensitivity and 90 to 98 percent specificity for chest radiographs.
* **Limits:** head and neck primaries (not breast), one centre, retrospective, reference standard is the CT itself, no confidence intervals.
* **Used by:** M4 test ladder (lung rows). A breast-cancer-specific accuracy source for chest radiography was searched for and not found; one search result is a pooled detection-rate review, which is not an accuracy measure.

### E23 — Between-Laboratory Spread of CA 15-3 Results (EQA programme) — `SECONDARY` (abstract-level; numbers machine-verified against the PubMed abstract)
* **Source:** Jia T, Zhang Z, Yue Y, et al. "The Current Status of CA15-3 Measurement Based on a Commutable External Quality Assessment Program." *Clin Lab*. 2026;72(10):2285-2292. doi:[10.7754/Clin.Lab.2025.251106](https://doi.org/10.7754/Clin.Lab.2025.251106). PMID:[42847942](https://pubmed.ncbi.nlm.nih.gov/42847942/). Excerpt: [`docs/evidence/excerpts/E23_jia_2026_ca153_eqa.md`](evidence/excerpts/E23_jia_2026_ca153_eqa.md).
* **Figures:** five EQA rounds 2023 to 2025 with 504 to 817 laboratories; within reagent classes the robust CV across laboratories ranged from 6.48 to 7.63 percent. The abstract states that reagents and methods differ and that different cut-offs should be used.
* **Limits:** Chinese national programme (not Nigerian laboratories); a spread across laboratories, not a bias estimate; abstract-level only.
* **Used by:** K5 lab-harmonisation study `experiments/EXP-K5-001` (to anchor the simulated between-laboratory spread; larger spreads are assumptions).

### E24 — GRUwE: Recurrent Model with Exponential Basis Functions for Irregular Time Series — `SECONDARY` (method description only; no performance figure is used)
* **Source:** Joshi A, Hauskrecht M. "Still Competitive: Revisiting Recurrent Models for Irregular Time Series Prediction." arXiv:2510.16161 (October 2025). Excerpt: [`docs/evidence/excerpts/E24_joshi_2025_gruwe.md`](evidence/excerpts/E24_joshi_2025_gruwe.md).
* **Content used:** the two-step state update (time-triggered exponential decay of the hidden state; observation-triggered GRU update with the mask as an input). Implemented in `vigil_ml.k4.GRUwE`.
* **Limits:** non-oncology benchmarks; a preprint (E11 cites a TMLR 2026 version that was not retrieved); no figure from it is relied on.
* **Used by:** K4 study `experiments/EXP-K4-001`.

### E25 — ESMO (Pan-Asian adapted) Follow-up Recommendations for Early Breast Cancer — `SECONDARY` (guideline consensus statements; quoted text machine-checked against the open-access full text)
* **Source:** Park KH, Loibl S, Sohn J, et al. "Pan-Asian adapted ESMO Clinical Practice Guidelines for the diagnosis, treatment and follow-up of patients with early breast cancer." *ESMO Open*. 2024;9(5):102974. doi:[10.1016/j.esmoop.2024.102974](https://doi.org/10.1016/j.esmoop.2024.102974). PMID:[38796284](https://pubmed.ncbi.nlm.nih.gov/38796284/). Excerpt: [`docs/evidence/excerpts/E25_park_2024_esmo_followup.md`](evidence/excerpts/E25_park_2024_esmo_followup.md).
* **Figures:** follow-up visits every 3 months in the first 3 years (every 6 months for low-risk disease), every 6 months in years 4 to 5, annually after; the interval "can be adapted to the risk of relapse"; routine laboratory tests and tumour markers are **not recommended** in asymptomatic patients [I, D], though they "may be considered on an individual basis" [V, C].
* **Limits:** consensus guideline for Asian systems; says nothing about Nigerian pathways; recommendation 8d runs against marker-based surveillance, so the K6 simulation study makes no claim about real patients.
* **Used by:** K6 active-sensing study `experiments/EXP-K6-001` (named baseline schedules; the counter-indication is stated in its limits).

### E26 — Federated Averaging (iterative model averaging of locally computed updates) — `SECONDARY` (method source; abstract-level)
* **Source:** McMahan HB, Moore E, Ramage D, Hampson S, Agüera y Arcas B. "Communication-Efficient Learning of Deep Networks from Decentralized Data." AISTATS 2017. PMLR 54:1273-1282. [PMLR proceedings](https://proceedings.mlr.press/v54/mcmahan17a.html). arXiv:[1602.05629](https://arxiv.org/abs/1602.05629). Excerpt: [`docs/evidence/excerpts/E26_mcmahan_2017_fedavg.md`](evidence/excerpts/E26_mcmahan_2017_fedavg.md). No Crossref DOI: PMLR 54 does not register one; the arXiv `10.48550/arXiv.1602.05629` identifier is not in Crossref.
* **Figures:** none copied. The paper names Federated Learning as training by aggregating locally-computed updates without uploading the training data, and FederatedAveraging as iterative model averaging of locally trained weights.
* **Limits:** mobile-device language and image models, not clinical laboratories; robustness claims are empirical on their datasets.
* **Used by:** M12 federated/DP feasibility study `experiments/EXP-M12-001` (to name the FedAvg algorithm).

### E27 — Differentially private SGD (clip, noise, privacy accounting) — `SECONDARY` (method source; abstract-level)
* **Source:** Abadi M, Chu A, Goodfellow I, McMahan HB, Mironov I, Talwar K, Zhang L. "Deep Learning with Differential Privacy." CCS 2016. doi:[10.1145/2976749.2978318](https://doi.org/10.1145/2976749.2978318). arXiv:[1607.00133](https://arxiv.org/abs/1607.00133). Excerpt: [`docs/evidence/excerpts/E27_abadi_2016_dp_sgd.md`](evidence/excerpts/E27_abadi_2016_dp_sgd.md).
* **Figures:** none copied into the study. The method is: at each SGD step, clip the ℓ2 norm of each example's gradient, average, add Gaussian noise, and account the privacy loss. A full-text numerical example (q = 0.01, σ = 4, δ = 10⁻⁵, T = 10000 → ε ≈ 1.26 under the moments accountant) is used only as a unit-test target for Vigil's accountant.
* **Limits:** MNIST/CIFAR, not clinical data; (ε, δ)-DP is not an NDPA/GDPR determination.
* **Used by:** M12 federated/DP feasibility study `experiments/EXP-M12-001` (to name DP-SGD and the accountant test).

### E6 — Radiotherapy Capacity in Nigeria — `SECONDARY` / `STALE`
* ~200M population, estimated shortfall of ~280 LINACs by IAEA benchmarks; high out-of-pocket costs and machine downtime. Current national facility assessment pending hospital partnership data.
* Sources: PMC7456314; local press reports.
* **Used by:** Treatment delay and harm modeling (Module M7).

### E7 — Nigerian Breast Cancer Presentation, Staging, and Subtypes — `SECONDARY` (downgraded by overseer 2026-10-17: saved 'verbatim' excerpt contains numbers absent from the retrievable source; see scripts/audit_excerpts.py and docs/progress/VERDICT-P5A.md)
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
