# ADR 0015: Radiotherapy Scheduling Operational Basis, Consent, and Multi-Course Integrity

## Status
Accepted

## Context
In hospital radiotherapy departments, linear accelerators (LINACs) are scarce physical resources operating under rigid operational constraints (e.g. 16 treatment fraction slots per machine per day). When machine breakdowns or maintenance outages occur, department-wide capacity must be rescheduled dynamically to mitigate excess cancer recurrence harm and prevent treatment gaps (Module M7, Master Plan §6.7).

This raises two architectural and governance questions:
1. **Multi-Course Disambiguation:** Can a patient have multiple radiotherapy courses concurrently or consecutively (e.g. breast chest-wall irradiation and subsequent palliative bone metastasis irradiation)? If so, internal solver mapping keyed purely on `patient_id` causes course collisions where one course overwrites another in `course_map`.
2. **Consent and Operational Scheduling Basis:** If a registered oncology patient has not granted app/research consent, or has withdrawn general surveillance consent under the Nigeria Data Protection Act 2023 (NDPA), should their treatment course be omitted from the CP-SAT machine slot optimization solver?

## Decision

### 1. Multi-Course Entity Disambiguation
We introduce `course_id: Optional[str] = None` onto `PatientCourse` and `SlotAllocation` in `vigil_ml.scheduler`.
- When courses are mapped into solver variables, the unique scheduling entity identifier is `uid = p.course_id if p.course_id else p.patient_id`.
- The solver tracks both `patient_start_days` and `course_start_days`, resolving start dates, fraction deliveries, machine assignments, and marginal explanations uniquely per course.
- In `vigil_api.api.endpoints.continuity`, `course_map` is keyed strictly by `course.id` (`course_map[c.id] = c`), completely eliminating the course collision defect.

### 2. Legal Basis: Clinical Treatment Relationship & Facility Capacity
Under the Nigeria Data Protection Act 2023 (NDPA Act No. 34 of 2023, Section 30(1)(b) & Section 30(1)(i)) and international medical device standards:
- The allocation of physical beam-time on radiotherapy machines directly affects patient safety, treatment continuity, and department physics calibration.
- Operating the capacity solver exclusively on "consented" patients would create phantom capacity: omitted patients would still physically show up for treatment, resulting in machine double-booking, catastrophic queue breakdowns, and unmeasured clinical delays for all patients.
- Therefore, the mathematical solver includes **all active courses within the facility** under the direct *clinical treatment relationship / medical management / vital interest* basis (NDPA §30(1)(b)).

### 3. Patient Privacy and Transparency Guarantees
To prevent any circumvention of patient data protection rights:
1. **No External Disclosures:** The solver runs internally within the secure facility context. The schedule solve API endpoint (`POST /continuity/schedule/solve`) surfaces abstract assignments.
2. **Explicit Transparency Metrics:** The solve response explicitly reports:
   - `patients_included: int` — total number of distinct patients whose active courses were evaluated in the solver.
   - `patients_unconsented_included: int` — number of distinct patients included on the operational treatment-relationship basis who lack active app/surveillance consent.
3. **Consent Filtering on Individual Listings:** Individual clinical listings (`GET /continuity/courses` and `GET /continuity/ledger`) strictly enforce active patient consent filtering (`verify_patient_consent` / `has_active_consent`). Patients who have withdrawn consent are excluded from listings, and unconsented identifiers are never leaked to clinicians or clerks.

## Consequences
- **Positive:** Mathematically sound physical machine scheduling without double-booking or phantom capacity.
- **Positive:** Multi-course cancer trajectories (adjuvant + palliative) are handled without dictionary collision.
- **Positive:** Transparent reporting of operational inclusion metrics (`patients_included`, `patients_unconsented_included`) aligns with NDPA governance.
- **Positive:** Individual data access, export, and viewing remain strictly subject to verified active patient consent.
