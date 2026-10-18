# Vigil Human-Factors Heuristic Usability Evaluation

**Document ID:** VIG-UX-001  
**Version:** 1.0.0-rc.1  
**Standard Compliance:** IEC 62366-1:2015 / AMD 1:2020 (Usability Engineering for Medical Devices), Nielsen-Molich 10 Heuristics, WCAG 2.2 AA  
**Scope:** Expert review of the 5 core operator surfaces across Clinician Workstation and Patient & Family Companion  

---

## 1. Methodology & Evaluation Framework

In accordance with IEC 62366-1 Clause 5.7 (User Interface Design and Verification) and Master Plan WP8.3, this evaluation conducts a systematic, non-participant heuristic analysis of the Vigil user interface. The review assesses risk of user error, automation bias, cognitive overload, and accessibility compliance.

### Evaluated UI Surfaces
1. **Clinician Triage Queue (`/workstation/triage`)**
2. **Longitudinal Adjudication View (`/workstation/patients/:id`)**
3. **Bad-News Mode & Patient Disclosure Gateway**
4. **Treatment Continuity & Radiotherapy Scheduler (`/workstation/continuity`)**
5. **Quality & Missed-Signal Audit View (`/workstation/quality`)**

### Severity Classification (Nielsen Severity Rating)
- **0 - No Problem:** Cosmetic or stylistic preference.
- **1 - Cosmetic Problem:** Low priority; need not be fixed unless time allows.
- **2 - Minor Usability Problem:** Low clinical risk; causes minor frustration or friction.
- **3 - Major Usability Problem:** Moderate clinical risk; confusing or induces cognitive delay.
- **4 - Usability Catastrophe:** High clinical risk; high likelihood of causing user error or medical mismanagement.

---

## 2. Heuristic Audit by Screen

### Screen 1: Clinician Triage Queue (`/workstation/triage`)
| ID | Heuristic Violations | Observed UI Element & Potential Error | Severity | Clinical Safety Impact | Implemented Mitigation |
|:---|:---|:---|:---:|:---|:---|
| **HE-1.1** | *Error Prevention* (Nielsen #5) | Clinician attempting to dismiss an elevated alert without documented disposition. | **4** | Patient with active recurrence lost to follow-up (Original Vigil Failure Mode). | **No-Dismissal Invariant:** UI enforces mandatory disposition dropdown + free-text rationale. Cannot dismiss via single click. |
| **HE-1.2** | *Recognition rather than Recall* (Nielsen #6) | Bare alert score (e.g. "0.82") displayed without confidence interval or baseline context. | **3** | Misinterpretation of point estimate; automation bias. | UI displays bounded interval $[q_{0.025}, q_{0.975}]$, uncertainty tier, and primary contributing analytes. |
| **HE-1.3** | *Visibility of System Status* (Nielsen #1) | Stale risk scores showing when new laboratory specimens are pending analysis. | **2** | Clinician acts on outdated data. | Prominent "Pending Lab Specimen" badge with specimen collection timestamp. |

### Screen 2: Longitudinal Adjudication View (`/workstation/patients/:id`)
| ID | Heuristic Violations | Observed UI Element & Potential Error | Severity | Clinical Safety Impact | Implemented Mitigation |
|:---|:---|:---|:---:|:---|:---|
| **HE-2.1** | *Match Between System and Real World* (Nielsen #2) | Analytes plotted on arbitrary vertical scales without standard clinical units (e.g., U/mL, mg/dL). | **3** | Erroneous interpretation of trajectory slope across multi-analyte panels. | Strict UCUM units labelled on all axes; biological reference change values (RCV) plotted as shaded confidence envelopes. |
| **HE-2.2** | *Aesthetic and Minimalist Design* (Nielsen #8) | Cluttered time-series charts presenting 10+ analytes simultaneously on mobile or low-res display. | **2** | Visual fatigue and missed subtle trend signals. | Default grouped display by organ tropism (Hepatic, Bone, Renal, Systemic) with single-toggle comparison. |
| **HE-2.3** | *Flexibility and Efficiency of Use* (Nielsen #7) | Ordering follow-up repeat labs requires navigating away from patient timeline. | **2** | Workflow interruption during busy multidisciplinary team (MDT) meetings. | In-line "One-Click Follow-Up Action" drawer with pre-populated repeat lab interval recommendations. |

### Screen 3: Bad-News Mode & Patient Disclosure Gateway
| ID | Heuristic Violations | Observed UI Element & Potential Error | Severity | Clinical Safety Impact | Implemented Mitigation |
|:---|:---|:---|:---:|:---|:---|
| **HE-3.1** | *User Control and Freedom* (Nielsen #3) | Automatic disclosure of critical recurrence risk to patient/caregiver companion prior to physician consultation. | **4** | Severe psychological distress or panic in patient/family without clinician guidance (Hazard H14). | **Bad-News Mode:** Escalate-tier results withheld until clinician explicitly clicks "Release Disclosure" or 72-hour grace period elapses. |
| **HE-3.2** | *Help Users Recognize, Diagnose, and Recover from Errors* (Nielsen #9) | Clinician accidentally unlocking disclosure prematurely. | **3** | Unintentional release of unconfirmed test findings. | Double-confirmation modal with plain-language consequence preview and explicit override audit record. |
| **HE-3.3** | *Match Between System and Real World* (Nielsen #2) | Plain-language patient translation using overly clinical Latinate jargon (e.g., "bone metastasis"). | **3** | Patient confusion, compliance failure, or fatalistic anxiety. | Multilingual plain-language summary in English, Nigerian Pidgin, Yoruba, Hausa, Igbo validated against community glossary. |

### Screen 4: Treatment Continuity & Radiotherapy Scheduler (`/workstation/continuity`)
| ID | Heuristic Violations | Observed UI Element & Potential Error | Severity | Clinical Safety Impact | Implemented Mitigation |
|:---|:---|:---|:---:|:---|:---|
| **HE-4.1** | *Error Prevention* (Nielsen #5) | Clinician blindly applying automated CP-SAT machine reallocation without simulation validation. | **4** | Over-reliance on unvalidated simulation policy causing suboptimal patient delays (Hazard H10, H16). | Prominent amber badge: **`unvalidated in simulation`**; requires manual review and sign-off for each schedule adjustment. |
| **HE-4.2** | *Consistency and Standards* (Nielsen #4) | Inconsistent display of delay days vs treatment gap days. | **2** | Confusion between cumulative wait time and inter-fraction interruptions. | Explicit dual counters: "Pre-Treatment Delay (Days)" vs "Unplanned Interruption (Days)" with separate harm calculations. |
| **HE-4.3** | *Visibility of System Status* (Nielsen #1) | Linac machine breakdown status not clearly tied to affected patient schedule cards. | **3** | Operator schedules patient on offline machine. | Machine status indicators (Operational, Maintenance, Down) highlighted with red warning borders on dependent slot assignments. |

### Screen 5: Quality & Missed-Signal Audit View (`/workstation/quality`)
| ID | Heuristic Violations | Observed UI Element & Potential Error | Severity | Clinical Safety Impact | Implemented Mitigation |
|:---|:---|:---|:---:|:---|:---|
| **HE-5.1** | *Match Between System and Real World* (Nielsen #2) | Audit reporting using punitive or accusatory terminology (e.g. "negligence", "physician failure"). | **3** | Defensiveness, clinician disengagement, hostile audit reception. | **Neutral Descriptive Register (ADR 0016):** strictly objective terms: "unaddressed signal patterns", "delayed follow-up rate", "opportunity window". |
| **HE-5.2** | *Privacy & Confidentiality* (Nielsen #5) | Displaying small patient cell counts ($n < 5$) in public or regional audit reports. | **4** | Patient re-identification hazard in specialized clinical subgroups. | **Small-Cell Suppression (k >= 5):** Any stratum with $n < 5$ is masked with `< 5` and aggregated into broad categories. |

---

## 3. Accessibility & Usability Engineering Summary

- **WCAG 2.2 AA Compliance:** All text elements exhibit minimum 4.5:1 contrast ratio (7:1 in patient-facing companion mode). Touch targets on companion views measure $\ge 48 \times 48\text{ px}$.
- **Keyboard Navigation:** Full focus trap and logical tab order enforced across all modal dialogs, drawers, and form controls.
- **Screen Reader Support:** ARIA attributes (`aria-expanded`, `aria-describedby`, `role="alert"`, `aria-live="polite"`) implemented across dynamic timeline updates and alert counters.
