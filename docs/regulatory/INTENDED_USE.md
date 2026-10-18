# Vigil Precision Oncology — Intended Use & Indications for Use Statement

> [!WARNING]
> **DRAFT — UNREVIEWED REGULATORY ARTIFACT**
> This document is an engineering draft prepared for pre-market governance alignment.
> It has NOT been reviewed, audited, or approved by a Qualified Person, Regulatory Affairs Director, or Competent Authority (e.g., US FDA, Nigeria NAFDAC, EU Notified Body).
> NOT AUTHORIZED FOR CLINICAL USE, REGULATORY SUBMISSION, OR OPERATIONAL DEPLOYMENT.

---

## 1. Intended Use Statement
Vigil is a Software as a Medical Device (SaMD) clinical decision-support platform intended for use by qualified healthcare professionals (oncologists, surgical oncologists, radiation oncologists, oncology nurses) to assist in the longitudinal surveillance, recurrence risk stratification, and radiotherapy continuity coordination for adult female patients previously treated for invasive breast carcinoma.

Vigil ingests longitudinal serial laboratory biomarker values (CA 15-3, CEA), patient-reported symptom reports, and clinical treatment course metadata to provide:
1. **Plausibility & Anomaly Adjudication (M3):** Automated detection of specimen collection/handling anomalies, assay drift, and physiologically implausible biomarker spikes.
2. **Sequential Recurrence Detection (K2):** Early statistical detection of true biological relapse using patient-specific baseline modeling and sequential Bayes change-point detection.
3. **Structured Clinical Explanations (M5):** Verifiable clinical narratives synthesizing trajectory trends and actionable recommendations for clinician review.
4. **Follow-Up Coordination (M6):** Automated tracking, prompt scheduling, and escalation of necessary diagnostic follow-up tasks (e.g., repeat blood draws, staging scans).
5. **Radiotherapy Continuity Optimization (M7):** Mathematical resource allocation and queue scheduling to minimize treatment interruptions and tumor repopulation harms across constrained linear accelerators.

**Vigil is an adjunct decision-support tool. It does not perform autonomous diagnosis, does not select specific systemic therapies, and does not replace the professional judgement of a licensed physician.**

---

## 2. Indications for Use
Vigil is indicated for adult patients (age $\ge 18$ years) diagnosed with Stage I–III invasive breast carcinoma who have completed definitive primary surgical intervention and are undergoing routine post-treatment surveillance or adjuvant radiotherapy.

---

## 3. Target User Population
* **Primary Users:** Licensed medical, clinical, and radiation oncologists.
* **Secondary Users:** Registered oncology nurses, clinical navigators, and hospital clinic clerks operating under clinical supervision.
* **Non-Clinical Users:** Health facility quality leads and system administrators (access restricted to aggregate quality metrics and operational audit logs).
* **Companion Users:** Consented patients and designated family caregivers via delegated, scoped read-only summaries.

---

## 4. Environment of Use
* Secondary and tertiary healthcare facilities, outpatient cancer centers, and radiotherapy departments in high-resource and low-to-middle-income resource-constrained settings.
* Client platforms: Modern web browsers (Chrome, Firefox, Safari, Edge) on desktop workstations and mobile tablet devices supporting TLS 1.3 encryption.
* Operates under variable network connectivity with robust offline mutation buffering and replay capabilities.

---

## 5. Contraindications
* Pediatric patients ($< 18$ years of age).
* Patients with primary malignancies other than invasive breast carcinoma.
* Emergency triage of acute life-threatening oncologic emergencies (e.g., spinal cord compression, superior vena cava syndrome, febrile neutropenia).
* Stand-alone autonomous radiation dose calculation or direct machine control of radiotherapy delivery units.

---

## 6. Warnings, Precautions & Limitations
1. **Biomarker Non-Specificity:** Biomarker fluctuations (CA 15-3, CEA) may arise from non-malignant etiologies (e.g., benign hepatic, pulmonary, or inflammatory diseases). All alerts require clinical correlation and imaging confirmation before initiating intervention.
2. **Biomarker Non-Secretors:** Up to 20% of recurrent breast cancers do not secrete elevated serum markers. Vigil cannot exclude recurrence in the presence of clinically concerning physical symptoms.
3. **Model Validation Status:** Scheduling optimization models (M7 CP-SAT) are explicitly badged `"unvalidated in simulation"` until prospective clinical trial endpoints are validated (ADR 0014, Study M7-TWIN).
4. **Human-in-the-Loop Safeguard:** All clinical actions require explicit clinician review, adjudication, and signed electronic acknowledgement.
