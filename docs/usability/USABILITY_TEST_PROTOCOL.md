# Vigil Clinical Usability Study Protocol (Formative & Summative)

**Protocol ID:** VIG-CLIN-USAB-001  
**Version:** 1.0.0-rc.1  
**Standard Compliance:** IEC 62366-1:2015 / AMD 1:2020, DECIDE-AI Guidelines (Stages 1 & 2), ISO 14971:2019  
**Status:** DRAFT-FOR-ETHICAL-REVIEW (Prepared for National Health Research Ethics Committee - NHREC)  

---

## 1. Study Objectives & Hypotheses

This protocol governs the human-factors usability evaluation of the Vigil Precision Oncology Platform across representative clinical oncology environments in Nigeria.

### Primary Objectives
1. Evaluate whether attending clinicians, oncology registrars, and oncology nurses can safely, accurately, and rapidly navigate the Clinician Workstation without safety-critical use errors.
2. Quantify overall usability, cognitive workload, and user satisfaction using standardized psychometric instruments.
3. Test the clinical efficacy of built-in safety controls: the **No-Dismissal Safety Invariant**, **Bad-News Mode**, and the **`unvalidated in simulation`** warning badge on RT schedule recommendations.

### Hypotheses
- **H_USAB-1 (Usability):** Mean System Usability Scale (SUS) score will achieve $\ge 80.0$ (Grade A, excellent usability).
- **H_USAB-2 (Efficacy):** Clinical task completion rate will exceed $95.0\%$ across all standard surveillance and triage scenarios.
- **H_USAB-3 (Safety):** Zero ($0\%$) uncritical acceptance of unvalidated scheduler recommendations and zero unrecorded alert dismissals.

---

## 2. Participant Cohort & Inclusion Criteria

A purposive sample of $N = 12$ clinical oncology healthcare providers will be recruited across two partner tertiary cancer centers (University College Hospital Ibadan and Lagos University Teaching Hospital):

### Stratification
| Role | Sample ($N$) | Professional Experience | Primary Focus Surface |
|:---|:---:|:---|:---|
| **Consultant Medical Oncologists** | 4 | $\ge 5$ years post-fellowship | Triage Queue, Adjudication, Test Ladder |
| **Oncology Residents / Registrars** | 4 | $\ge 2$ years oncology training | Longitudinal History, Follow-Up Guardian |
| **Specialist Breast Care Nurses** | 4 | $\ge 3$ years oncology nursing | Bad-News Mode, Companion PWA, Multilingual Glossary |

### Inclusion & Exclusion Criteria
- **Inclusion:** Licensed medical practitioner or registered nurse actively involved in outpatient breast cancer follow-up and multidisciplinary tumor boards.
- **Exclusion:** Prior direct involvement in the software engineering or design of Vigil.

---

## 3. Standardized Clinical Test Scenarios

Participants will interact with a simulated workstation running against realistic, synthetically generated longitudinal patient trajectories (`vigil-sim` generated):

### Scenario 1: Subtle Biomarker Elevation with High Measurement Noise (M3)
- **Patient Profile:** 52F, Stage IIA ER+/HER2- breast cancer, 18 months post-surgery.
- **Event:** CA 15-3 rises from 22 to 28 U/mL across 60 days.
- **Challenge:** Evaluate whether the change exceeds the biological Reference Change Value (RCV) or represents assay noise.
- **Target Action:** Correctly recognize low probability of true biological change; schedule routine follow-up rather than urgent imaging.

### Scenario 2: Accelerated Doubling Time Requiring Confirmatory Specimen (M4/M6)
- **Patient Profile:** 46F, Triple-Negative Breast Cancer (TNBC), 12 months post-chemotherapy.
- **Event:** CEA doubles from 4.2 to 8.9 ng/mL with new bone ache symptoms.
- **Target Action:** Order confirming repeat specimen draw within 14 days and initiate secondary imaging referral; document mandatory clinical disposition.

### Scenario 3: Bad-News Mode Consultation & Patient Release (M8)
- **Patient Profile:** 58F presenting with confirmed distant recurrence.
- **Event:** Clinician reviews dossier, conducts in-person consultation, and unlocks patient Companion access.
- **Target Action:** Verify that patient-facing summary is locked prior to consultation; review plain-language translations in Yoruba/Pidgin; successfully release disclosure.

### Scenario 4: LINAC Breakdown Triage & Equity Verification (M7)
- **Facility Profile:** 2 LINACs; LINAC-01 suffers magnetron failure (7-day MTTR).
- **Event:** Review proposed CP-SAT schedule reallocation.
- **Target Action:** Inspect the **`unvalidated in simulation`** badge; verify that palliative patients maintain urgency bounds ($\le 3$ days); manually sign off on curative TNBC continuation priority.

---

## 4. Evaluated Endpoints & Metrics

1. **System Usability Scale (SUS):** 10-item Likert scale administered immediately post-session. Target: $\ge 80.0$.
2. **Task Completion Rate (TCR):** Binary score per task (Completed independently / Required assistance / Failed). Target: $\ge 95.0\%$.
3. **Time to First Clinical Action (TFCA):** Seconds from viewing dossier to placing laboratory/imaging order or disposition. Target: $\le 60$ seconds.
4. **NASA-TLX (Task Load Index):** Cognitive workload assessment across 6 dimensions (Mental demand, Physical demand, Temporal demand, Performance, Effort, Frustration). Target: Mean score $\le 40/100$.
5. **Safety-Critical Error Rate:** Count of severe errors (e.g., attempt to bypass confirmation, unverified schedule application, improper disclosure release). Target: $0$.

---

## 5. Ethical Considerations & Data Management

1. **Informed Consent:** Voluntary written informed consent obtained prior to participation. Participants may withdraw at any time without institutional penalty.
2. **De-Identification & Privacy:** All sessions recorded via screen-capture and audio are assigned randomized participant IDs (`P-01` .. `P-12`). No participant name or identifying detail appears in transcripts.
3. **Synthetic Data Exclusivity:** All patient profiles used during the evaluation are 100% synthetic; no real patient data is exposed or stored during usability testing.
4. **Data Retention:** Usability recordings and survey matrices are encrypted with AES-256 and stored on institutional air-gapped storage for 3 years, after which digital shredding is mandated.
