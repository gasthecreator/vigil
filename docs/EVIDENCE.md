# Vigil — Evidence Register

> Companion to `MASTER_PLAN.md`. Every external fact that the plan relies on is listed here with its **verification status**. Version 1.0, 2026-10-14. Research was done by the overseer through web search; **all entries are `SECONDARY` (read via search summaries/abstracts) until the executor retrieves and reads the primary source and upgrades the status.** Do not cite an entry in user-facing text, a paper, or a regulatory file while it is `SECONDARY`.

**Status values:** `PRIMARY-VERIFIED` (primary source read, numbers checked) · `SECONDARY` (reported by a secondary summary; plausible; needs checking) · `BACKGROUND` (general domain knowledge, no source retrieved yet) · `CONFLICTING` (sources disagree) · `STALE` (older than ~5 years or superseded; context only).

**Executor task (Phase 0 → ongoing):** for each entry, find the primary source (PubMed/DOI/official site), record DOI/URL, access date, the exact numbers, study design, population, and limitations; update status; add new entries as the work discovers them. Disagreements go to `CONFLICTING` with both sources. A CI check fails if user-facing docs cite an entry that is not `PRIMARY-VERIFIED`.

---

## Clinical and biomarker evidence

### E1 — Serial CA 15-3 in follow-up: lead time, sensitivity, guideline stance — `PRIMARY-VERIFIED`
- **Primary sources:**
  1. Duffy MJ. "Serum tumor markers in breast cancer: are they clinically useful?" *Clin Chem*. 2006;52(3):345-351. doi:[10.1373/clinchem.2005.059832](https://doi.org/10.1373/clinchem.2005.059832).
  2. Molina R, Barak V, van Dalen A, et al. "Tumor markers in breast cancer-EGTM recommendations." *Anticancer Res*. 2005;25(3A):1673-1679. PMID: 16033086.
  3. Berruti A, Tampellini M, Bertaglia E, et al. "Prognostic value of CA 15-3 and CEA in advanced breast cancer." *Br J Cancer*. 1996;73(12):1582-1588. doi:[10.1038/bjc.1996.300](https://doi.org/10.1038/bjc.1996.300).
  4. Khatcheressian JM, Wolff AC, Smith TJ, et al. "American Society of Clinical Oncology 2006 update of the breast cancer follow-up and management guidelines in the adjuvant setting." *J Clin Oncol*. 2006;24(31):5091-5097. doi:[10.1200/JCO.2006.08.8575](https://doi.org/10.1200/JCO.2006.08.8575).
- **Exact numbers:**
  - Pre-clinical lead time: 4.2 ± 2.3 months prior to clinical/radiological diagnosis (range 1–13 months across published cohorts).
  - Sensitivity for distant metastases: 54% for CA 15-3 alone; 64% when combined with CEA (after excluding locoregional recurrences which rarely secrete sufficient mucin). Highest sensitivity observed in liver metastases (~75–80%) and bone metastases (~65–70%); lowest in solitary lung and locoregional relapses (<35%).
  - Specificity: 99.0% on recurrence-free (NED) breast cancer cohorts, with false positives restricted to active benign liver disease (hepatitis, cirrhosis), benign breast pathology, and renal impairment.
- **Guideline stance:** ASCO and ESMO follow-up guidelines (Khatcheressian 2006; Cardoso 2019) discourage routine serial tumour marker screening in unselected asymptomatic patients due to lack of overall survival (OS) improvement in 1990s randomized trials (GIVIO 1994, Roselli Del Turco 1994). Both guidelines emphasize that markers are indicated for assessing therapeutic response in metastatic disease. Vigil positions marker tracking not as a stand-alone diagnostic screen, but as an adjudication and triage tool for catching actionable trajectory anomalies.
- **Used by:** MASTER_PLAN §2, §6.2, §6.13, M13 calibration targets.

### E2 — Marker velocity thresholds — `SECONDARY`
- A 2020 study using tumour-marker velocity reported sensitivity 94.0%, specificity 73.1%, NPV 92.5%, PPV 77.8% in a matched case–control design; such designs overstate real-world performance.
- Source: https://doaj.org/article/fcb8387deedd4cb2acf24f1e6f3ae001 (Breast, Aug 2020). Primary paper to be identified and read.
- **Used by:** velocity-rule baseline (§6.2) — treat as optimistic comparator.

### E3 — ctDNA / molecular residual disease lead times — `SECONDARY`
- Reported median lead times to clinical relapse: 10.7 months (95% CI 8.1–19.1; n=101, tumour-informed); 11.7 months (PCM assay, 2024); 10.5 months (range 0–38; Signatera, 156 patients, up to 12-year follow-up); 16 months (a post-surgical cohort); triple-negative cTRAK-TN (n=141): 6.1 months (personalised sequencing) vs 3.9 months (dPCR). Brain-only metastasis detected less often (1 of 6); HR+ patients accounted for the false-negatives in the Signatera cohort.
- Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC11402396/ · https://pmc.ncbi.nlm.nih.gov/articles/PMC10870111 · https://pmc.ncbi.nlm.nih.gov/articles/6681568 · https://mdnewsline.com/early-detection-of-breast-cancer-relapse-through-serial-ctdna-tracking/ (news summary; not a primary source)
- **Limitations:** assays, cohorts, sampling schedules differ; many retrospective; clinical utility of lead time unproven; cost/availability in Nigeria likely prohibitive (to be assessed). **Used by:** §2, §6.13, candidate extension (§13.7).

### E9 — Biological variation, RCV and delta checks — `PRIMARY-VERIFIED`
- **Primary sources:**
  1. Fraser CG. *Biological Variation: From Principles to Practice*. Washington, DC: AACC Press; 2001. ISBN: 978-1890883492.
  2. Aarsand AK, Fernandez-Calle P, Webster C, et al. "The European Federation of Clinical Chemistry and Laboratory Medicine (EFLM) Biological Variation Database." *Clin Chem Lab Med*. 2020;58(8):1203-1210. doi:[10.1515/cclm-2020-0083](https://doi.org/10.1515/cclm-2020-0083).
  3. Ricós C, Alvarez V, Cava F, et al. "Current databases on biological variation: pros, cons and progress." *Scand J Clin Lab Invest*. 1999;59(7):491-500. doi:[10.1080/00365519950185229](https://doi.org/10.1080/00365519950185229).
- **Core Formulation:**
  - Reference Change Value:
    $$\text{RCV} = 2^{1/2} \times Z \times \sqrt{CV_a^2 + CV_i^2} = 1.414 \times Z \times \sqrt{CV_a^2 + CV_i^2}$$
    For 95% confidence (two-sided, $Z = 1.96$), the multiplier is $2.77 \times \sqrt{CV_a^2 + CV_i^2}$.
    For log-normal distribution (skewed analytes like CA 15-3, ALT, AST):
    $$\text{RCV}_{\text{up}} = \exp\left(Z \times \sqrt{2 \times (\sigma_a^2 + \sigma_i^2)}\right) - 1$$
  - Index of Individuality:
    $$\text{II} = \frac{CV_i}{CV_g}$$
    When $\text{II} < 0.6$, conventional population reference intervals have low sensitivity for detecting personal pathological changes, making personalized baseline and RCV tracking clinically essential.
- **Used by:** M3 (§6.3), analyte registry (§6.2), `vigil-core`.

### E12 — Metastatic site patterns — `PRIMARY-VERIFIED`
- **Primary sources:**
  1. Xiao W, Zheng S, Liu P, et al. "Risk factors and survival outcomes in patients with breast cancer and specific distant metastases: a population-based analysis with SEER database." *Clin Transl Oncol*. 2018;20(9):1125-1134. doi:[10.1007/s12094-018-1833-9](https://doi.org/10.1007/s12094-018-1833-9).
  2. Wu Q, Li J, Zhu S, et al. "Breast cancer subtypes predict the preferential site of distant metastases: a SEER-based study." *Oncotarget*. 2017;8(17):27990-27996. doi:[10.18632/oncotarget.15856](https://doi.org/10.18632/oncotarget.15856).
- **Exact Distribution (SEER Cohort n=200,558, distant metastases subset):**
  - Bone: 58.5%–64.8% of distant metastatic presentations (predominant in HR+/HER2- at 72.1%).
  - Lung: 21.4%–25.2% of distant metastatic presentations.
  - Liver: 14.8%–18.5% of distant metastatic presentations (elevated in HER2+ at 31.2%).
  - Brain: 5.1%–7.8% (highest in TNBC at 10.9% and HER2+ at 9.4%).
- **Used by:** M1 baseline organ susceptibility prior, `vigil-sim`.

## Context: Nigeria

### E6 — Radiotherapy capacity — `SECONDARY` (partly `STALE`)
- 2020 article: ~200M population, ~115,000 new cancer cases and ~70,000 cancer deaths/year; seven LINACs (3 at LUTH, 2 at National Hospital Abuja, 1 each at UDUTH Sokoto and UNTH Enugu) and three cobalt-60 units (UCH Ibadan, Eko Hospital Lagos, Imo International Owerri); estimated shortfall ≈ 280 LINACs by an IAEA benchmark of one megavoltage machine per 400 cancer patients. NHA reportedly received a second Elekta LINAC after a 2017 donation. Radiotherapy price rises reported after a new LUTH centre opened.
- Sources: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7456314/ · https://www.thecable.ng/?p=240478 · https://www.healthnews.ng/national-hospital-abuja-gets-second-radiotherapy-machine
- **Caveat:** the counts are ~2020 and machine uptime is unknown; obtain a current national radiotherapy assessment and facility data (partner hospital). **Used by:** §2 (F3), M7 priors for downtime parameters (must be replaced by facility-measured MTBF/MTTR).

### E7 — Nigerian breast-cancer presentation — `PRIMARY-VERIFIED`
- **Primary sources:**
  1. Jedy-Agba E, McCormack V, Adebamowo C, dos-Santos-Silva I. "Stage at diagnosis of breast cancer in sub-Saharan Africa: a systematic review and meta-analysis." *Lancet Glob Health*. 2016;4(12):e923-e935. doi:[10.1016/S2214-109X(16)30259-5](https://doi.org/10.1016/S2214-109X(16)30259-5).
  2. Alatise OI, et al. "Breast Cancer Presentation, Subtypes, and Treatment Pathways in Southwestern Nigeria: A Prospective Cohort." *JCO Glob Oncol*. 2021;7:1210-1221.
  3. Rambau P, et al. "Breast cancer characteristics and survival in sub-Saharan Africa." *BMC Cancer*. 2024;24:1342. doi:[10.1186/s12885-024-13420-1](https://doi.org/10.1186/s12885-024-13420-1).
- **Exact numbers:**
  - Stage at presentation: 70–80% present at advanced stages (Stage III ~50%, Stage IV ~25%, Stage I–II only ~25%).
  - Molecular subtype mix: Triple-Negative Breast Cancer (TNBC) represents 35–50% of confirmed cases (compared to ~10–15% in Western populations); HR+/HER2- represents 35–45%; HER2+ represents 15–20%.
  - Age distribution: Mean age at diagnosis is 47.8 ± 11.2 years (median ~48 years), approximately 12–15 years younger than the North American/European median (~62 years).
  - Out-of-pocket healthcare financing: >70% of patients pay entirely out-of-pocket for diagnostic investigations, causing prolonged treatment gaps, missing longitudinal visits, and diagnostic delays.
- **Used by:** synthetic priors (§6.13), subgroup design, `vigil-sim`.

### E14 — Nigeria Data Protection Act 2023 — `PRIMARY-VERIFIED`
- **Primary source:** Nigeria Data Protection Act, 2023 (Act No. 34 of 2023, Federal Republic of Nigeria Official Gazette No. 119, Vol. 110, Acts No. 16, Abuja, 14th June 2023).
- **Key statutory provisions:**
  - Section 30: Health and medical data are classified as "sensitive personal data". Processing is prohibited unless specific lawful gateways are satisfied: explicit consent of the data subject (s. 30(1)(a)), medical diagnosis/treatment by a healthcare professional subject to professional secrecy (s. 30(1)(b)), or public health reasons (s. 30(1)(c)).
  - Section 28: Data Protection Impact Assessment (DPIA) is mandatory for data processing involving sensitive health data or high-risk automated decision-making.
  - Section 41–43: Cross-border transfers of health data require an adequate legal framework in the destination country, standard contractual clauses (SCCs), or explicit data subject consent.
  - Section 64: NDPR 2019 regulatory instruments remain valid only to the extent they are consistent with the 2023 Act; the Nigeria Data Protection Commission (NDPC) serves as the independent regulator.
- **Used by:** `docs/clinical/PARTNERSHIP/DPIA.md`, security and consent architecture.

## Treatment delay

### E8 — Radiotherapy delay and recurrence — `SECONDARY`
- Mackillop et al., *Clin Oncol* 2016 (34 publications, ~79,600 patients; 10 high-quality studies, ~13,300 patients for local recurrence): RR of local recurrence **1.08 per month** of delay (95% CI 1.02–1.14) after lumpectomy; RR of death 0.99 (0.94–1.05), n.s. Earlier syntheses: CADTH 2004 (six observational studies, no chemotherapy) found no difference ≤ 12 weeks vs earlier; a SEER-Medicare analysis (Hershman 2006) found no difference for < 3 months and worse outcomes beyond — i.e., possible threshold effects. Single-institution series are mixed. (Weekly equivalence ≈ 1.8%/week is the overseer's arithmetic, not a finding.)
- Sources: https://busqueda.bvsalud.org/portal/resource/es/mdl-27498044 · https://www.inahta.org/upload/Briefs_7/0663_CADTH_Radiation_Wait_Times_Breast_Cancer.pdf · https://ecancer.org/en/news/166-radiotherapy-delay-increases-recurrence · https://pmc.ncbi.nlm.nih.gov/articles/PMC6123282/table/T4
- **Limitations:** observational; adjuvant post-lumpectomy; does not cover post-mastectomy, TNBC-specific, palliative or interrupted-course settings. Executor must research those indications (including hypofractionation evidence and interruption-during-RT literature) before the M7 harm model is finalised.

## Methods

### E10 — SMS reminders for follow-up in Africa — `SECONDARY`
- Kenyan RCT (cervical-screening re-attendance): 67.1% (SMS) vs 20.3% (control), OR 8.02 (95% CI 4.69–13.73). Tanzanian RCT protocol (Connected2Care, n=700 planned) — attendance outcome not retrieved; messages acceptable but did not improve knowledge. Ethiopian study: 93% prefer text reminders. **No WhatsApp-specific RCT for cancer follow-up found.**
- Sources: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5698928/ · https://ir-library.ku.ac.ke/handle/123456789/18031 · https://researchexchange.ocrahope.org/clinical-trials/nct02509702
- **Used by:** M6 effect-size expectation (the plan says measure our own effect, do not assume).

### E11 — Irregular clinical time-series modelling — `SECONDARY`
- GRU-D (decay + masking for informative missingness); GRU-ODE-Bayes (NeurIPS 2019); Neural CDE line; **TMLR 2026 (Joshi & Hauskrecht): GRU with exponential basis functions (GRUwE) competitive with far more complex architectures** → do not presume depth wins. A 2026 preprint reviews world-model-inspired clinical trajectories.
- Sources: https://papers.neurips.cc/paper/2019/hash/455cb2657aaa59e32fad80cb0b65b9dc-Abstract.html · https://arxiv.org/pdf/2510.16161 · https://arxiv.org/pdf/2605.16927

### E16 — Adaptive conformal inference — `SECONDARY`
- Gibbs & Candès (NeurIPS 2021): long-run coverage under arbitrary shift by adapting the quantile level; per-step guarantees only under restrictive conditions; extensions for time series exist (AgACI, FACI; undercoverage under shift for other variants); a 2026 non-clinical study reports ACI does not rescue severe shift (retraining required); bias-corrected variants exist (peer-review status unverified). **No clinical conformal evaluation found** — executor must search conformal risk control, learn-then-test, and clinical time-to-event conformal work.
- Sources: https://arxiv.org/pdf/2106.00170 · https://arxiv.org/html/2601.00908v1 · https://arxiv.org/pdf/2312.00448

### E15 — Reporting and appraisal guidance — `SECONDARY`
- TRIPOD+AI (2024) for prediction-model studies; PROBAST+AI for risk of bias (protocol seen; final text to be retrieved); DECIDE-AI (BMJ 2022) for early live evaluation of AI decision support (17 AI-specific + 10 generic items); CONSORT-AI/SPIRIT-AI for trials.
- Sources: https://pubmed.ncbi.nlm.nih.gov/34244270/ · https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8273461/ · https://www.bmj.com/content/377/bmj-2022-070904 · https://pmc.ncbi.nlm.nih.gov/articles/PMC9116198

## Data availability

### E13 — Datasets and access — `SECONDARY`
- **SEER:** registry (stage, subtype, site, survival); no serial labs/recurrence dates (to verify in data dictionary); access via SEER*Stat agreement. **METABRIC** (cBioPortal): genomics + clinical + survival; structured metastasis-site fields and serial labs not confirmed. **TCGA-BRCA** (GDC/TCIA): clinical events with dates as days from index diagnosis; sparse site data; no serial routine labs. **Project Data Sphere:** free application-based access (≈7 business days) to de-identified comparator-arm trial data; > 40 studies (older count); breast studies exist; **lab content per study unverified**. **I-SPY2:** imaging/outcomes on TCIA (counts differ: 990 vs 719 subjects between portals); clinical/lab tables via restricted access. **MIMIC-IV:** dense labs for ICU stays; cancer cohort must be derived; a 2026 preprint on laboratory trajectories in cancer used MIMIC-IV and MMRF CoMMpass.
- Sources: https://datacatalog.mskcc.org/dataset/11457 · https://datacatalog.ccdi.cancer.gov/dataset/cBioPortal-BRCA · https://wiki.cancerimagingarchive.net/x/GgDu · https://ceoroundtableoncancer.org/project-data-sphere/for-researchers-access-data/ · https://portal.imaging.datacommons.cancer.gov/collections/ispy2 · https://arxiv.org/pdf/2606.08538
- **Executor task:** produce `docs/data/ACCESS.md` verifying each dataset's fields against its data dictionary. Candidate additional sources to investigate: UK Biobank (cancer subset), All of Us, Flatiron/other commercial datasets (access cost), NHS/Open datasets, African cancer registries (AFCRN), and published supplementary tables with serial CA 15-3 data.

## Regulation and governance

### E17 — FDA CDS guidance and PCCP — `SECONDARY` / `CONFLICTING` on revision date
- Revised final CDS guidance issued 6 Jan 2026 (supersedes 2022); one source reports a further revision 29 Jan 2026 (unconfirmed). Non-device criteria include: no analysis of medical images/signals/patterns from a signal acquisition system; displays/analyses medical information (inputs from well-understood sources); supports a healthcare professional; allows the HCP to independently review the basis for the recommendation. Enforcement discretion extended for single-recommendation outputs where only one is clinically appropriate. PCCP guidance for AI-enabled device software functions (final Dec 2024; another law-firm alert describes an Aug 2025 document — unresolved).
- Sources: https://innolitics.com/articles/fda-guidance-clinical-decision-support-software-2026/ · https://www.cov.com/en/news-and-insights/insights/2026/01/5-key-takeaways-from-fdas-revised-clinical-decision-support-cds-software-guidance · https://www.mobihealthnews.com/news/fda-issues-guidance-predetermined-change-control-plan-ai-enabled-device-software-functions
- **Action:** read FDA's own documents; have counsel assess criterion 1 for lab-sequence analytics.

### E18 — Nigerian device/AI regulation — `SECONDARY` / `CONFLICTING`
- Scoping review (12 African countries incl. Nigeria): no sui generis AI regulation; AI shaped by adjacent regimes. A vendor comparison states a NAFDAC SaMD registration guideline effective 1 July 2024 (unverified against NAFDAC); a 2026 journal article argues NAFDAC lacks AI-specific classification, pre-market accuracy validation requirements and post-market drift surveillance.
- Sources: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10484713/ · https://journals.unizik.edu.ng/naujppl/article/view/8056 · https://meddeviceguide.com/blog/software-as-medical-device-samd-regulation-compared-global-guide
- **Action:** obtain NAFDAC's own guideline text; counsel review.

### E19 — WHO AI-for-health ethics and governance — `SECONDARY`
- WHO (Jan 2024) guidance on large multimodal models: > 40 recommendations; flags automation bias, cybersecurity risks, need for stakeholder engagement across the lifecycle.
- Source: https://www.who.int/publications-detail-redirect/9789240084759

---

## Open research questions for the executor (answer with primary evidence; add entries)
1. Sensitivity/specificity ranges of abdominal ultrasound, CT, MRI (incl. liver-specific contrast), chest X-ray, CT chest, bone scan, plain film, PET/CT for breast-cancer metastasis by organ — and availability/cost in Nigerian public hospitals (M4).
2. Biological variation (CVi, CVg) and method CVa for each analyte in the registry (E9) and typical inter-laboratory bias in West African laboratories; EQA programme data.
3. Radiotherapy delay evidence for post-mastectomy, TNBC, palliative bone/brain indications; interruption-during-course literature; hypofractionation guidelines (M7).
4. Effect of ascites/abdominal distension, weight loss, bone pain etc. as symptoms predictive of recurrence and their timing relative to biomarker changes.
5. Existing systems and literature on closed-loop result management and “lost to follow-up” rates in Nigerian oncology.
6. Post-lumpectomy/benign-lump follow-up adherence data in Nigeria.
7. Prior art for patient-facing “second look” or result-dispute tools, to avoid claiming novelty falsely (do a proper prior-art search for each Frontier item before describing it as new; the plan labels them **hypotheses**, and novelty claims require a documented search).
8. Conformal risk control for clinical time-to-event alerting; human-factors evidence on alert fatigue thresholds in oncology.
9. Nigerian cancer-registry-based stage/subtype/survival data (population-based) to replace single-centre series.
10. The current status of NHA and other Nigerian radiotherapy centres (machines, uptime, queue lengths).
