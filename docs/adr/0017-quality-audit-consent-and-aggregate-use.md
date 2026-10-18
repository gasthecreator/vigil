# ADR 0017: Quality Audit Consent Enforcement and Aggregate Use Governance

## Status
Accepted

## Context
ADR 0016 established institutional quality improvement as a lawful operational basis for retrospective clinical quality audits. However, as identified in Overseer Verdict P7B (Condition P13-F), relying on general aggregate quality improvement grounds to include patients who have explicitly withdrawn consent violates patient autonomy under the Nigeria Data Protection Act (NDPA 2023) Section 28 (Sensitive Personal Data) and modern biomedical clinical governance standards.

When a patient explicitly revokes or withdraws consent for oncology surveillance processing, their choice must be respected comprehensively across both prospective care management and retrospective analytical pipelines. Failing to filter out withdrawn patients from retrospective cohort extraction creates a compliance risk and breaches the ethical trust between patients and the healthcare facility.

## Decision

### 1. Precedence of Patient Consent Over Aggregate Audit Inclusion
Vigil strictly honors patient consent status in retrospective quality audits:
* **Active Consent Required:** Only patients with currently valid, non-withdrawn consent (`has_active_consent(patient_id, db, current_user) == True`) are extracted for facility-level retrospective quality audits.
* **Consent Withdrawal / Revocation:** Any patient who has withdrawn consent, whose consent has expired, or who has never consented to surveillance monitoring is immediately excluded from the retrospective audit trajectory pool.
* **No Retrospective Override:** Institutional quality assurance mandates cannot override a patient's affirmative statutory withdrawal of consent.

### 2. Server-Side Extraction Invariant
The database extraction pipeline (`_extract_trajectories_from_db` in `vigil_api.api.endpoints.quality`) evaluates consent status for every patient record prior to constructing `AuditTrajectory` objects. Unconsented or withdrawn patient records are skipped before any clinical observations or follow-up tasks are accessed.

### 3. Separation of Facility Data and Synthetic Benchmarks
Facility audit data and synthetic benchmark populations are strictly isolated:
* The default audit request evaluates only consented real facility patients (`include_synthetic_benchmark=False`).
* An empty facility reports zero audited patients, rather than padding results with fabricated records.
* When requested explicitly (`include_synthetic_benchmark=True`), the synthetic benchmark runs in isolation and is explicitly flagged in narrative summaries with `"SYNTHETIC BENCHMARK ONLY - this is not facility data."`

### 4. Clinician-Attributable Action Verification
To measure clinical care rather than pipeline automation, `action_recorded` is determined solely by verified clinician actions:
* Clinician acknowledgement of an alert (`AlertAcknowledgement`) with recorded disposition and rationale.
* Completed clinical follow-up tasks (`FollowUpTask` with `status == "completed"` and recorded `completed_at`).
* System-generated automated tasks that remain pending are never counted as recorded clinical actions.

## Consequences
- Patient autonomy is preserved: patients who withdraw consent are excluded from retrospective analysis.
- Facility audits reflect genuine clinical actions rather than automated system artifact tasks.
- Verified by automated tests in `tests/acceptance_p13` and `apps/api/tests/test_quality_api.py`.
