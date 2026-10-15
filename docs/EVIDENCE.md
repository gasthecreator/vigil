# Vigil — Evidence Register

> Companion to `MASTER_PLAN.md`. Every external fact that the plan relies on is listed here with its **verification status**. Version 1.0, 2026-10-14. Research was done by the overseer through web search; **all entries are `SECONDARY` (read via search summaries/abstracts) until the executor retrieves and reads the primary source and upgrades the status.** Do not cite an entry in user-facing text, a paper, or a regulatory file while it is `SECONDARY`.

**Status values:** `PRIMARY-VERIFIED` (primary source read, numbers checked) · `SECONDARY` (reported by a secondary summary; plausible; needs checking) · `BACKGROUND` (general domain knowledge, no source retrieved yet) · `CONFLICTING` (sources disagree) · `STALE` (older than ~5 years or superseded; context only).

**Executor task (Phase 0 → ongoing):** for each entry, find the primary source (PubMed/DOI/official site), record DOI/URL, access date, the exact numbers, study design, population, and limitations; update status; add new entries as the work discovers them. Disagreements go to `CONFLICTING` with both sources. A CI check fails if user-facing docs cite an entry that is not `PRIMARY-VERIFIED`.

---

## Clinical and biomarker evidence

### E1 — Serial CA 15-3 in follow-up: lead time, sensitivity, guideline stance — `SECONDARY`
- Reported: serial markers can detect recurrence pre-clinically with lead times of roughly 2–9 months; a 1,023-patient cohort found CA 15-3 elevated before diagnosis in ~41% of recurrences (lead 4.2 ± 2.3 months), sensitivity ~54% for CA 15-3 (64% combined with CEA) after excluding locoregional recurrences, specificity ~99% (444 NED patients); a 1996 prospective study (n=209) reported 68.2% sensitivity; stage I prospective cohort: mean lead 6.3 months over bone scintigraphy for bone metastases, CA 15-3 not elevated in locoregional disease; sensitivity highest in liver metastases, lowest in locoregional relapse.
- **Guideline stance:** ESMO/ASCO follow-up recommendations (history, physical exam, annual mammography) discourage routine serial tumour markers in asymptomatic early breast cancer because of no demonstrated survival benefit; markers are most useful for monitoring therapy in advanced disease not assessable by imaging.
- Sources (search results): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1977334/ · https://pmc.ncbi.nlm.nih.gov/articles/PMC8282974/ · https://research.universityofgalway.ie/en/publications/a-prospective-evaluation-of-ca15-3-in-stage-i-carcinoma-of-the-br-3/ · https://doi.org/10.1007/BF00690183
- **Limitations:** older, mostly small single-centre studies; most guideline statements need re-reading on asco.org/esmo.org for the current versions. **Used by:** MASTER_PLAN §2, §6.2, §6.13, M13 calibration targets (targets must be re-derived from primary papers).

### E2 — Marker velocity thresholds — `SECONDARY`
- A 2020 study using tumour-marker velocity reported sensitivity 94.0%, specificity 73.1%, NPV 92.5%, PPV 77.8% in a matched case–control design; such designs overstate real-world performance.
- Source: https://doaj.org/article/fcb8387deedd4cb2acf24f1e6f3ae001 (Breast, Aug 2020). Primary paper to be identified and read.
- **Used by:** velocity-rule baseline (§6.2) — treat as optimistic comparator.

### E3 — ctDNA / molecular residual disease lead times — `SECONDARY`
- Reported median lead times to clinical relapse: 10.7 months (95% CI 8.1–19.1; n=101, tumour-informed); 11.7 months (PCM assay, 2024); 10.5 months (range 0–38; Signatera, 156 patients, up to 12-year follow-up); 16 months (a post-surgical cohort); triple-negative cTRAK-TN (n=141): 6.1 months (personalised sequencing) vs 3.9 months (dPCR). Brain-only metastasis detected less often (1 of 6); HR+ patients accounted for the false-negatives in the Signatera cohort.
- Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC11402396/ · https://pmc.ncbi.nlm.nih.gov/articles/PMC10870111 · https://pmc.ncbi.nlm.nih.gov/articles/6681568 · https://mdnewsline.com/early-detection-of-breast-cancer-relapse-through-serial-ctdna-tracking/ (news summary; not a primary source)
- **Limitations:** assays, cohorts, sampling schedules differ; many retrospective; clinical utility of lead time unproven; cost/availability in Nigeria likely prohibitive (to be assessed). **Used by:** §2, §6.13, candidate extension (§13.7).

### E9 — Biological variation, RCV and delta checks — `BACKGROUND`
- Reference Change Value `RCV = √2·Z·√(CVa²+CVi²)` (log-normal variant for skewed analytes), index of individuality, personalised reference intervals; the EFLM Biological Variation Database is the standard source of CVi/CVg per analyte. **No source was retrieved in this research pass.** Executor must retrieve the EFLM database entries and the foundational papers (e.g., Fraser; Harris) and record each analyte's CVi, CVg, method CVa class, and citation.
- **Used by:** M3 (§6.3), analyte registry (§6.2).

### E12 — Metastatic site patterns — `SECONDARY`
- SEER analysis of 200,558 female breast cancer patients (2014–2023): among those with distant metastasis, bone 21.3%, lung 16.1%, liver 9.2%, brain 2.9% (patterns classified into 15 combinations); subtype strongly associated with site (HR+/HER2− prone to bone-only metastasis).
- Sources: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12284020/ · https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5438624/ · https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5432264/
- **Limitation:** SEER has registry-level site data; no serial labs or recurrence timing; SEER site fields have known under-ascertainment (to be verified in the SEER data dictionary). **Used by:** M1.

## Context: Nigeria

### E6 — Radiotherapy capacity — `SECONDARY` (partly `STALE`)
- 2020 article: ~200M population, ~115,000 new cancer cases and ~70,000 cancer deaths/year; seven LINACs (3 at LUTH, 2 at National Hospital Abuja, 1 each at UDUTH Sokoto and UNTH Enugu) and three cobalt-60 units (UCH Ibadan, Eko Hospital Lagos, Imo International Owerri); estimated shortfall ≈ 280 LINACs by an IAEA benchmark of one megavoltage machine per 400 cancer patients. NHA reportedly received a second Elekta LINAC after a 2017 donation. Radiotherapy price rises reported after a new LUTH centre opened.
- Sources: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7456314/ · https://www.thecable.ng/?p=240478 · https://www.healthnews.ng/national-hospital-abuja-gets-second-radiotherapy-machine
- **Caveat:** the counts are ~2020 and machine uptime is unknown; obtain a current national radiotherapy assessment and facility data (partner hospital). **Used by:** §2 (F3), M7 priors for downtime parameters (must be replaced by facility-measured MTBF/MTTR).

### E7 — Nigerian breast-cancer presentation — `SECONDARY`
- Small single-centre series: 68.2% stage III/IV (n=89) and 80.2% ≥ stage III (n=607, 2010–2018); among tested tumours 35.5–65% triple-negative (n=107 Lagos: 35.5%; n=58 tested: ~53%; 607-patient database: 43.5% of the ~22% with IHC); mean ages ≈ 47–52 years. Denominators and testing rates differ; no pooled population-based estimate was found.
- Sources: https://bmccancer.biomedcentral.com/articles/10.1186/s12885-024-13420-1 · https://journal.gcps.edu.gh/index.php/pmjg/article/view/41 · https://pmc.ncbi.nlm.nih.gov/articles/PMC8394611 · https://omjournal.org/IssueText.aspx?issId=3560
- **Used by:** synthetic priors (§6.13), subgroup design; must be replaced with registry data when available (e.g., Nigerian cancer registries / GLOBOCAN) — executor to research.

### E14 — Nigeria Data Protection Act 2023 — `SECONDARY` / `CONFLICTING` on NDPR status
- Health information is sensitive personal data; processing needs a lawful basis (e.g., consent; vital interests; public-health law); principles of lawfulness, purpose limitation, minimisation, accuracy, storage limitation, security; s.28 requires a DPIA for likely high-risk processing; regulator: Nigeria Data Protection Commission. Sources conflict on whether the 2019 NDPR remains in force (KPMG says replaced; a Mondaq analysis reads s.64 as saving it).
- Sources: https://fpf.org/blog/nigerias-new-data-protection-act-explained/ · https://assets.kpmg.com/content/dam/kpmg/ng/pdf/the-nigeria-data-protection-act-2023.pdf · https://www.mondaq.com/nigeria/data-protection/1366934/the-nigerias-data-protection-act-2023-a-look-at-key-provisions · https://blog.babalakinandco.com/?p=1454
- **Executor task:** read the Act's gazetted text; extract sensitive-data conditions, cross-border transfer rules, breach-notification deadlines, DPO requirements; counsel to confirm.

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
