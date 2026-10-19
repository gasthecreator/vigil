# Vigil Human-Factors Cognitive Walkthroughs

**Document ID:** VIG-UX-002  
**Version:** 1.0.0-rc.1  
**Methodology:** Wharton et al. Cognitive Walkthrough for Clinical Software (IEC 62366-1 Clause 5.7)  
**Standard Compliance:** IEC 62366-1:2015, Master Plan §10, §11, WP8.3  

---

## 1. Methodology & Evaluation Protocol

A cognitive walkthrough is a task-centered usability inspection method that focuses on how easy it is for new or intermittent users to learn a system by exploration. For each step of a critical user journey, four core psychological questions are answered:

1. **Q1: Will the user try to achieve the right effect?** (Does the user's intent match the system state?)
2. **Q2: Will the user notice that the correct action is available?** (Is the button, link, or control visible?)
3. **Q3: Will the user associate the correct action with the desired effect?** (Is the label/icon clear?)
4. **Q4: If the correct action is performed, will the user see that progress is being made?** (Is feedback immediate and unambiguous?)

---

## 2. Walkthrough 1: Attending Oncologist Triaging High-Urgency Recurrence Alert

**Persona:** Dr. Kemi Alabi, Consultant Medical Oncologist at Lagos University Teaching Hospital (LUTH). Busy clinic, 45 outpatients queued.  
**Clinical Scenario:** Patient Mrs. A (48F, Stage IIA ER+/HER2- breast cancer, 24 months post-lumpectomy) has sudden CEA doubling and rising CA 15-3. System generates an Escalate-tier alert.  
**Clinical Goal:** Review laboratory velocity, adjudicate signal versus assay variation, order repeat confirmation blood draw within 14 days, and withhold premature release to patient app until biopsy/confirmation.

| Step | Action | Q1: Correct Intent? | Q2: Action Noticeable? | Q3: Correct Association? | Q4: Clear Feedback? | Evaluation & Safety Controls |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
| **1.1** | Scan Triage Queue for critical cases. | **Yes.** Queue defaults to urgency-sorted alerts. | **Yes.** Red/Amber badge with high-contrast text clearly visible. | **Yes.** "Escalate (95% CI: 0.78–0.89)" links directly to patient dossier. | **Yes.** Clicking patient row opens dossier in 40 ms. | **Pass.** Minimal visual clutter; sorting is explicit. |
| **1.2** | Inspect multi-analyte longitudinal trajectory. | **Yes.** Wants to rule out lab instrument error. | **Yes.** Trajectory tab is selected by default; reference ranges shaded. | **Yes.** "Adjudication (M3)" badge indicates assay noise likelihood is low (< 5%). | **Yes.** Interactive tooltips display date, exact value, and analytical CV. | **Pass.** No silent unit conversion; biological variation envelopes visible. |
| **1.3** | Order 14-day repeat specimen (Follow-up Guardian M6). | **Yes.** Standard practice: confirm before imaging. | **Yes.** Primary action button "Order Confirming Specimen" is prominent. | **Yes.** Text explicitly specifies analyte panel and 14-day default window. | **Yes.** Modal confirms scheduled task in M6 escalation ladder. | **Pass.** Task automatically enters hospital follow-up tracking register. |
| **1.4** | Acknowledge alert with mandatory disposition. | **Yes.** Must document reason for MDT record. | **Yes.** Acknowledge panel docked at bottom of screen. | **Yes.** Dropdown contains standardized clinical dispositions (e.g. "Sample Redraw Ordered"). | **Yes.** Button enables only when disposition and free-text note are entered. | **Pass (No-Dismissal Invariant).** Enforces H1/H2 mitigation; cannot be dismissed without documentation. |

---

## 3. Walkthrough 2: Oncology Nurse Managing Bad-News Mode During Family Consultation

**Persona:** Nurse Folake, Breast Care Nurse Specialist. In-person consultation with patient Mrs. B and her adult daughter.  
**Clinical Scenario:** Confirmed hepatic recurrence. Clinician has completed clinical review and instructed the nurse to unlock the Companion summary so the family can read plain-language guidance at home.  
**Clinical Goal:** Ensure sensitive disclosure, walk the family through the bad-news guidance, and unlock the Companion record.

| Step | Action | Q1: Correct Intent? | Q2: Action Noticeable? | Q3: Correct Association? | Q4: Clear Feedback? | Evaluation & Safety Controls |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
| **2.1** | Confirm Bad-News lock status before screen sharing. | **Yes.** Must ensure sensitive diagnosis is not abruptly visible. | **Yes.** Prominent purple banner: "Bad-News Mode Active: Sensitive Details Locked". | **Yes.** Clear lock icon and explanation of family view restriction. | **Yes.** Family-facing screen confirms "Summary Pending Doctor Discussion". | **Pass (H14 Mitigation).** Prevents unguided panic. |
| **2.2** | Review plain-language summary in Yoruba. | **Yes.** Patient's mother speaks primarily Yoruba. | **Yes.** Language selector clearly visible in header (English, Pidgin, Yoruba, Hausa, Igbo). | **Partial.** Switching language renders machine-draft strings; glossary terms are marked `[UNREVIEWED DRAFT]` until H-118 native-speaker review (ADR-0029). | **Partial.** Text renders; treat copy as unreviewed draft only. | **Conditional pass.** UI switch works; native-speaker clinician review has not been done (H-118 OPEN). |
| **2.3** | Unlock disclosure for Companion PWA. | **Yes.** Clinician has conducted consultation; family needs home access. | **Yes.** "Release to Patient Companion" button in clinician drawer. | **Yes.** Button label specifies action; double-confirmation dialog appears. | **Yes.** Status badge transitions to "Released: Available to Patient". | **Pass.** Audit event recorded with nurse ID and timestamp. |

---

## 4. Walkthrough 3: Radiotherapy Treatment Planner Handling LINAC Breakdown

**Persona:** Babatunde, Chief Medical Physicist / RT Scheduling Officer at University College Hospital (UCH) Ibadan.  
**Clinical Scenario:** LINAC-02 develops magnetron fault; down for estimated 7 days. 45 patients active on course; demand exceeds single-machine capacity.  
**Clinical Goal:** Reallocate slots to prevent interruption harm on curative TNBC patients while maintaining palliative pain relief slots and ensuring algorithmic equity.

| Step | Action | Q1: Correct Intent? | Q2: Action Noticeable? | Q3: Correct Association? | Q4: Clear Feedback? | Evaluation & Safety Controls |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
| **3.1** | Flag LINAC-02 as "Down (Estimated MTTR: 7 days)". | **Yes.** Needs system to recognize slot capacity reduction from 32 to 16. | **Yes.** Machine status card on `/workstation/continuity` has status toggle. | **Yes.** Toggle sets state to "Down"; prompts for estimated repair duration. | **Yes.** Calendar slots for LINAC-02 immediately turn red with zero capacity. | **Pass.** Instant visual update of available capacity. |
| **3.2** | Review automated CP-SAT reallocation schedule. | **Yes.** Needs optimized sequence that minimizes interruption harm. | **Yes.** Banner presents "Proposed Reallocation Schedule (CP-SAT)". | **Yes.** Prominently badged: **`unvalidated in simulation`**; notice explains manual review requirement. | **Yes.** Table compares FCFS vs Proposed wait times and expected delay harm. | **Pass (H10/H16 Mitigation).** No automated auto-apply. Clinician must verify each move. |
| **3.3** | Confirm curated schedule and issue delay notices. | **Yes.** Approve validated moves and inform delayed adjuvant patients. | **Yes.** "Confirm & Issue Notices" button active. | **Yes.** Action triggers plain-language SMS/WhatsApp delay explanations. | **Yes.** Audit ledger confirms confirmed allocations; patient delay notice log populated. | **Pass.** Fairness bounds verified ($\le 5$ day disparity between subgroups). |

---

## 5. Walkthrough 4: Quality Lead Conducting Missed-Signal Audit

**Persona:** Dr. Ibrahim, Quality Improvement Lead at National Hospital Abuja.  
**Clinical Scenario:** Annual surveillance audit to identify unaddressed recurrent biomarker signals and regional referral disparities.  
**Clinical Goal:** Generate institutional audit report, verify small-cell suppression, and review unaddressed signal rates.

| Step | Action | Q1: Correct Intent? | Q2: Action Noticeable? | Q3: Correct Association? | Q4: Clear Feedback? | Evaluation & Safety Controls |
|:---:|:---|:---:|:---:|:---:|:---|:---:|
| **4.1** | Navigate to Quality & Audit view. | **Yes.** Dedicated sidebar icon for authorized Quality Lead / Admin. | **Yes.** "Quality Audit (M10)" in navigation. | **Yes.** Opens facility audit overview dashboard. | **Yes.** Summary metrics render in < 100 ms. | **Pass.** Strict RBAC enforcement (blocked for unprivileged roles). |
| **4.2** | Inspect unaddressed signal patterns by clinic stratum. | **Yes.** Wants to identify which clinics experience delay. | **Yes.** Stratified table by Tumor Subtype, Age Band, and Referral Distance. | **Yes.** Column headers use neutral terminology ("Unaddressed Signal Rate", "Delay Days"). | **Yes.** Subgroups with $n < 5$ show `< 5 (Suppressed)` badge. | **Pass (ADR 0016).** Neutral register and privacy suppression verified. |
| **4.3** | Export anonymized aggregate audit report for Ministry. | **Yes.** Required for national oncology surveillance benchmarking. | **Yes.** "Export Institutional Audit Report (PDF/JSON)" button. | **Yes.** Explicit confirmation that no individual identifiers or cell counts $< 5$ are included. | **Yes.** Cryptographically signed PDF downloads with SHA-256 manifest. | **Pass.** Zero-leakage compliance verified. |
