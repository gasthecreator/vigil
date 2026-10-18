# Incident report

> **Status: TEMPLATE, DRAFT-UNREVIEWED.** Copy to `docs/incidents/INC-YYYY-NNN.md` (create the folder at first use). Never put a patient's name, MRN or any direct identifier in this file; use the pseudonymous patient id from the system.

## 1. Header
| Field | Value |
|---|---|
| Incident id | INC-YYYY-NNN |
| Reported by (role, not name) | |
| Date/time noticed (UTC) | |
| Date/time it started, if known (UTC) | |
| System tier at the time | silent mode (T-Q) / live pilot (T-L) / other |
| Version (git SHA of the deployment) | |

## 2. Severity (pick the highest that applies)
| Class | Definition |
|---|---|
| **S1** | A patient or clinician was shown, or could have acted on, a wrong, withheld, or unvalidated result; withheld bad news reached a patient; data of a patient without consent was processed; silent mode failed |
| **S2** | A safety control did not work but nothing reached a patient or clinician; the audit chain failed verification; a wrong-unit or implausible value entered the record |
| **S3** | Data-quality or availability problem with no safety effect; a monitor could not run |
| **S4** | Cosmetic or documentation error |

## 3. What happened (facts only)
Describe what was observed, in order. Paste unedited log lines or response bodies where useful, after removing identifiers.

## 4. Immediate action
| Action | By (role) | Time (UTC) |
|---|---|---|
| Stop level applied (none / pause evaluation / return to silent / full stop), see `STOP-RULES.md` | | |
| Patients or clinicians affected informed | | |

## 5. Cause
- Direct cause:
- Why the existing controls did not prevent it (name the hazard id in `docs/safety/HAZARD_LOG.md` and the test that was supposed to catch it):
- Was the cause a code defect, a configuration error, a data problem, a procedure gap, or training?

## 6. Correction
| Change | Link (PR / commit) | Test that now fails without the change |
|---|---|---|
| | | |

A correction without a failing-first test is not accepted for S1 or S2.

## 7. Stop-rule check
Did this incident meet a trigger in `STOP-RULES.md` section 2 or 3? Which? Was the action taken within the required time?

## 8. Hazard log
Does the hazard log need a new hazard or a changed status/residual risk? Record the change in the same PR.

## 9. Sign-off
| Role | Name | Date |
|---|---|---|
| Operator | | |
| Clinical lead (required for S1 and S2) | | |
