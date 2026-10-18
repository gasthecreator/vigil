# ADR 0016: Missed-Signal Quality Audit Privacy, Register, and Consent Governance

## Status
Accepted

## Context
Vigil Module M10 provides institutional retrospective quality assurance by evaluating historical cancer surveillance trajectories to detect missed recurrence signals—instances where biomarker kinetics or alert algorithms flagged high probability of disease progression, but no timely clinical action (imaging order, biopsy, clinical consultation, or treatment change) was recorded in the hospital electronic record within a pre-specified window ($W_{\text{action}} = 30$ days).

Quality improvement is essential for patient safety, clinical guideline adherence, and equitable care delivery. However, automated clinical auditing introduces significant risks:
1. **Clinician demoralization and punitive misinterpretation:** Automated accusation or clinician finger-pointing impairs psychological safety, promotes defensive medicine, and leads to punitive sanctions rather than systemic root-cause resolution.
2. **Patient re-identification risk in small demographic cells:** Slicing aggregate quality data by intersectional strata (e.g. rare subtype × young age × specific clinic) creates micro-cells ($n < 5$) vulnerable to re-identification, violating the Nigeria Data Protection Act (NDPA 2023) and clinical ethics.
3. **Legal basis and consent scope:** While direct patient care requires treatment consent, retrospective quality audit and clinical safety governance operate under institutional quality improvement mandates and statutory public health exemptions.

## Decision

### 1. Mandatory Neutral and Descriptive Register
The M10 audit engine must adhere to a strictly factual and non-accusatory register:
* Permitted phrasing: *"signal present, action not recorded"*, *"no recorded imaging order within 30 days"*, *"surveillance interval exceeded"*.
* Strictly forbidden phrasing: any punitive, legalistic, or judgmental terminology such as "negligence", "error", "fault", "malpractice", "blame", or "missed diagnosis".
* No clinician identifiers (names, license numbers, staff IDs) may appear in audit summaries or system payloads.

### 2. Mandatory Small-Cell Suppression ($k \ge 5$)
To prevent deductive re-identification of patients in intersectional strata:
* All aggregate quality audit outputs enforce a strict $k$-anonymity floor of $k = 5$.
* Any stratum or breakdown cell where the patient count $n$ satisfies $1 \le n < 5$ is suppressed: the count is displayed as `"<5"` (or integer `-1` in API responses) and associated marginal percentages are omitted.
* Cells with $n = 0$ are explicitly reported as `0`.

### 3. Role-Based Access Control (RBAC) & Immutable Audit Trail
Access to the M10 Quality Audit service (`POST /api/v1/quality/audit`) is strictly restricted:
* Permitted roles: `quality_lead` and `admin`.
* Disallowed roles: `nurse_clerk`, `radiographer`, `clinician`, `patient`, `caregiver`.
* Every invocation of the quality audit engine is recorded immutably in the facility audit log with caller ID, role, timestamp, date range, and parameters.

### 4. Legal & Consent Basis
Under the Nigeria Data Protection Act (NDPA 2023) Part V (Exceptions) and international healthcare governance norms:
* Quality assurance, clinical audit, and patient safety monitoring are conducted under institutional legitimate interests for health facility operations and public health safety.
* De-identified aggregate statistics preserve patient anonymity while enabling hospital boards to benchmark delay metrics and allocate diagnostic resources to high-risk clinics.

## Consequences
- Quality teams obtain systemic visibility into surveillance bottlenecks without punitive clinician surveillance.
- Deductive re-identification is prevented mathematically across all reported demographic and disease slices.
- Access is enforced at the server routing boundary and verified by automated attack matrices.
