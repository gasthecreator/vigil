# Institutional Value Proposition & The Missed-Signal Audit (docs/clinical/PARTNERSHIP/VALUE-PROPOSITION.md)

**Platform:** Vigil Precision Oncology Platform (`gasthecreator/vigil`)  
**Target Audience:** Chief Medical Directors, Heads of Clinical Oncology, Directors of Clinical Research, and Chemical Pathology Leadership at Nigerian Academic Teaching Hospitals  
**Document Purpose:** Institutional Value Proposition & Missed-Signal Audit (M10) Specification  
**Version:** 1.0.0

---

## 1. Executive Summary: What Vigil Offers Your Institution

Teaching hospitals and tertiary cancer centers in Nigeria face immense clinical headwinds: severe oncology staff shortages, overcrowded clinics, diagnostic imaging backlogs, and patients bearing 100% of diagnostic costs out-of-pocket. 

The **Vigil Precision Oncology Initiative** partners with academic hospitals to study whether routine outpatient laboratory blood tests can support earlier recognition of metastatic breast cancer recurrence — as a **research and quality-audit** collaboration, not as a cleared medical device.

In exchange for collaborating on an ethically approved, de-identified retrospective chart review, Vigil offers **four institutional workstreams at no software licence fee** (subject to ethics, DUA, and the claim boundaries in [`PARTNER-PACKET.md`](PARTNER-PACKET.md)):

```
+---------------------------------------------------------------------------------+
|              WHAT VIGIL CAN OFFER YOUR HOSPITAL (RESEARCH SCOPE)                |
+---------------------------------------------------------------------------------+
|  1. The Missed-Signal Audit (M10)      | Confidential quality report on *your*  |
|                                        | extract (method verified on synthetic) |
|  2. Laboratory QC & RCV discussion     | RCV / delta-check support for pathology|
|  3. Academic Co-Authorship             | Shared manuscripts if a study completes|
|  4. Decision-support software (later)  | Only after real-data validation +      |
|                                        | pilot go/no-go (today: NO-GO / L0)      |
+---------------------------------------------------------------------------------+
```

---

## 2. Core Offering: The Missed-Signal Audit (Module M10)

The centerpiece of our institutional partnership is the **Missed-Signal Audit (M10)**. Overworked oncologists reviewing 60–80 patients in a single outpatient clinic often lack the time to manually plot 3-year multi-analyte laboratory curves. Consequently, subtle, consistent elevations in transaminases (ALT/AST), alkaline phosphatase (ALP), or tumor markers (CA 15-3/CEA) are frequently dismissed as benign laboratory noise or medication side effects until overt, symptomatic metastasis occurs.

The Missed-Signal Audit provides hospital leadership and oncology clinical directors with a confidential, rigorously analyzed institutional report answering five vital clinical questions:

1. **Prevalence of Missed Biomarker Signals:** In what percentage of historical metastatic recurrence cases was an objective biochemical anomaly present $\ge 60$ days before clinical restaging or symptom onset?
2. **Estimated Diagnostic Lead Time:** How many months earlier could diagnostic imaging (ultrasound, CT, MRI) or biopsy have been triggered if automated biological variation thresholds ($RCV$) were active? [E1, E2].
3. **Organ-Specific Tropism Correlation:** Did early asymptomatic elevations in transaminases correlate specifically with subsequent liver metastases, or alkaline phosphatase with skeletal metastases?
4. **Out-of-Pocket Interval Impact:** What was the clinical impact of appointment spacing (e.g., 90-day vs 180-day intervals) on late-stage presentation and patient survival?
5. **False-Alarm Rate in Practice:** If an automated alert had fired during historical follow-up, how many non-recurring patients would have received an alert (workload burden per 100 patient-years)?

---

## 3. Laboratory Quality Control & Biological Variation Calibration

Every clinical chemistry analyzer has inherent analytical imprecision ($CV_a$), and every human body has natural intra-individual biological variation ($CV_i$). Standard static reference intervals (e.g., ALT $< 40$ U/L) miss significant internal shifts (e.g., a patient whose baseline is 12 U/L jumping to 38 U/L is undergoing hepatic injury, yet appears "normal" on static lab printouts).

As part of the study, Vigil’s chemical pathology engineering team:
* Calculates institution-specific **Reference Change Values (RCV)**:
  $$\text{RCV} = 2^{1/2} \cdot Z \cdot \sqrt{CV_a^2 + CV_i^2}$$
* Validates your hospital's lab analyzer precision against international EFLM (European Federation of Clinical Chemistry and Laboratory Medicine) specifications.
* Provides your Department of Chemical Pathology with calibrated delta-check algorithms to flag pre-analytical collection errors and true clinical shifts directly in your Laboratory Information System (LIS).

---

## 4. Academic Publication & Global Scientific Eminence

* **Equitable Authorship:** Collaborating clinical oncologists, chemical pathologists, surgical oncologists, and health records specialists from your institution will serve as primary co-investigators and co-authors on all peer-reviewed manuscripts.
* **Target venues (aspirational):** If results warrant, manuscripts may be submitted to clinical oncology and health informatics journals (examples only: *JCO Global Oncology*, *BMC Cancer*, *Journal of Health Informatics in Africa*). Venue acceptance is not promised.
* **Regional data contribution:** A consented, de-identified longitudinal biomarker cohort from your institution would be a valuable West African research resource; “first” or “groundbreaking” status is not claimed here.

---

## 5. Decision-Support Platform Deployment & Training (conditional)

Only **after** retrospective real-data analysis under a frozen pre-registration, ethics approval, and an explicit pilot go/no-go (today the kit answers **NO-GO**; maturity L0):
* Clinics may be offered a **silent-mode** or decision-aid deployment of the research software (`docs/clinical/SILENT-MODE.md`), not an unsupervised care system.
* The stack is designed for on-premises hospital hardware (no mandatory cloud); NDPR/DPIA compliance still requires site legal review.
* Training materials exist as drafts in `docs/clinical/PILOT/`; competency recording is a human action (H-107).

---

## 6. Financial Terms: Absolute Cost Neutrality

* **Zero Financial Cost to Institution:** The Vigil Initiative funds all research data abstraction stipends, data capture software, and statistical computing resources.
* **Zero Cost to Patients:** Because this is a secondary retrospective chart-review study, no patients are billed or contacted.
* **Institutional Open Source Commitment:** All platform code is developed openly under non-commercial, public-benefit governance dedicated to improving breast cancer outcomes.

---

## 7. Next Steps to Initiate Partnership

1. **Protocol Presentation:** 30-minute virtual or in-person clinical briefing with your Oncology and Pathology Department heads.
2. **HREC Ethical Submission:** Collaborative submission of the pre-drafted ethics package (`ETHICS-APPLICATION.md`) to your Institutional Health Research Ethics Committee.
3. **DUA Execution:** Formal execution of the bilateral Data Use Agreement (`DUA-TEMPLATE.md`) guaranteeing institutional data ownership and privacy protections.
4. **Commencement:** Onboarding of data abstraction officers to begin the Missed-Signal Audit.

*For inquiries or to schedule an institutional briefing, please contact the Vigil Research Initiative at `gasthecreator/vigil`.*
