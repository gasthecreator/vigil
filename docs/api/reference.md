# API reference

*Generated from the running app by `scripts/generate_api_reference.py` — Vigil 0.1.0-alpha. Do not edit by hand; CI fails if it is stale.* Machine-readable schema: [`openapi.json`](openapi.json).

Every route requires authentication unless marked **public**. `GET /metrics` needs `Authorization: Bearer $VIGIL_METRICS_TOKEN` and is disabled (403) when no token is set.

## Alerts & Acknowledgement

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/alerts/` | auth | List active surveillance alerts | 200, 422 |
| GET | `/api/v1/alerts/stream` | auth | Server-Sent Events (SSE) stream for real-time alert updates | 200, 422 |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | auth | Acknowledge alert with mandatory clinical disposition | 200, 422 |

## Analytics & Cohort

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/analytics/cohort` | auth | Get Cohort Analytics | 200, 422 |
| POST | `/api/v1/analytics/seed-demo-cohort` | auth | Seed Demo Cohort | 201, 422 |

## Batch Observation Ingestion

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| POST | `/api/v1/observations/batch-import` | auth | Batch import observations from CSV or Excel through no-dismissal pipeline | 200, 422 |

## Cryptographic Audit Trail

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/audit/events` | auth | List recent audit events | 200, 422 |
| GET | `/api/v1/audit/verify` | auth | Verify cryptographic integrity of the audit log chain | 200, 422 |

## Family & Patient Companion (M8)

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/companion/share/{share_token}` | public | Access patient summary via scoped caregiver share token | 200, 422 |
| POST | `/api/v1/companion/share/{share_token}/disclosure/request-release` | public | Caregiver requests clinician release of sensitive diagnostic results on behalf of patient | 201, 422 |
| GET | `/api/v1/companion/share/{share_token}/observations/{obs_id}/explainer` | public | Access plain-language observation explainer via caregiver share token | 200, 422 |
| POST | `/api/v1/companion/share/{share_token}/symptoms` | public | Record patient symptom on behalf of patient via caregiver share token | 201, 422 |

## Follow-Up Guardian (M6)

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/follow-up/outreach` | auth | Export prioritized outreach list for clinic staff | 200, 422 |
| GET | `/api/v1/follow-up/reminders/receipts` | auth | List reminder delivery receipts | 200, 422 |
| POST | `/api/v1/follow-up/reminders/run` | auth | Execute reminder worker cycle using injectable clock | 200, 422 |
| POST | `/api/v1/follow-up/{task_id}/transition` | auth | Transition follow-up task status in state machine | 200, 422 |

## HL7 FHIR R4 Interoperability

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| POST | `/api/v1/fhir/Observation` | auth | Import HL7 FHIR R4 Observation resource through surveillance pipeline | 201, 422 |
| GET | `/api/v1/fhir/Observation/{id}` | auth | Export observation as HL7 FHIR R4 Observation resource | 200, 422 |

## HL7 v2 ORU^R01 Interoperability

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| POST | `/api/v1/hl7/oru-r01` | auth | Ingest HL7 v2 ORU^R01 unsolicited laboratory result message | 200, 422 |

## OCR lab drafts

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/patients/{id}/ocr-drafts` | auth | List Ocr Drafts | 200, 422 |
| POST | `/api/v1/patients/{id}/ocr-drafts` | auth | Create Ocr Draft | 201, 422 |
| GET | `/api/v1/patients/{id}/ocr-drafts/{draft_id}` | auth | Get Ocr Draft | 200, 422 |
| POST | `/api/v1/patients/{id}/ocr-drafts/{draft_id}/confirm` | auth | Confirm Ocr Draft | 201, 422 |
| POST | `/api/v1/patients/{id}/ocr-drafts/{draft_id}/reject` | auth | Reject Ocr Draft | 200, 422 |

## Offline Batch Sync

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| POST | `/api/v1/sync/batch` | auth | Process offline sync batch replay with idempotency and LWW conflict resolution | 200, 422 |

## Patients & Surveillance

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/patients/` | auth | List Patients | 200, 422 |
| POST | `/api/v1/patients/` | auth | Create Patient | 201, 422 |
| POST | `/api/v1/patients/rotate-keys` | auth | Rotate Patient Keys Endpoint | 200, 422 |
| GET | `/api/v1/patients/triage` | auth | Get Triage Queue | 200, 422 |
| GET | `/api/v1/patients/{id}` | auth | Get Patient Detail | 200, 422 |
| PATCH | `/api/v1/patients/{id}` | auth | Update Patient | 200, 422 |
| POST | `/api/v1/patients/{id}/baseline` | auth | Submit Baseline Profile | 200, 422 |
| POST | `/api/v1/patients/{id}/consent` | auth | Update or grant patient consent record | 201, 422 |
| POST | `/api/v1/patients/{id}/disclosure/lock` | auth | Clinician re-locks disclosure for a patient | 200, 422 |
| POST | `/api/v1/patients/{id}/disclosure/request-release` | auth | Patient or caregiver requests clinician release of bad-news diagnostic results | 201, 422 |
| POST | `/api/v1/patients/{id}/disclosure/unlock` | auth | Unlock Patient Disclosure | 200, 422 |
| POST | `/api/v1/patients/{id}/labs` | auth | Submit Lab Result | 200, 202, 422 |
| GET | `/api/v1/patients/{id}/observations` | auth | List patient clinical observations | 200, 422 |
| POST | `/api/v1/patients/{id}/observations` | auth | Unit-safe observation ingestion calling M3, K2, and M5 | 201, 422 |
| GET | `/api/v1/patients/{id}/observations/{obs_id}/explainer` | auth | Get verified plain-language result explainer for patient/family | 200, 422 |
| GET | `/api/v1/patients/{id}/risk-history` | auth | List patient serial risk assessments | 200, 422 |
| POST | `/api/v1/patients/{id}/second-look` | auth | Submit Second Look Request | 201, 422 |
| GET | `/api/v1/patients/{id}/shares` | auth | List Caregiver Shares | 200, 422 |
| POST | `/api/v1/patients/{id}/shares` | auth | Create Caregiver Share | 201, 422 |
| DELETE | `/api/v1/patients/{id}/shares/{share_id}` | auth | Revoke Caregiver Share | 200, 422 |
| POST | `/api/v1/patients/{id}/simulate` | auth | Simulate Future Lab | 200, 422 |
| GET | `/api/v1/patients/{id}/symptoms` | auth | List Patient Symptoms | 200, 422 |
| POST | `/api/v1/patients/{id}/symptoms` | auth | Record Patient Symptom | 201, 422 |
| GET | `/api/v1/patients/{id}/trajectory` | auth | Get Patient Trajectory | 200, 422 |

## Quality & Missed-Signal Audit (M10)

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| POST | `/api/v1/quality/audit` | auth | Run Quality Audit | 200, 422 |
| GET | `/api/v1/quality/audit/latest` | auth | Get Latest Quality Audit | 200, 422 |

## Resource-Aware Test Ladder (M4)

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/test-ladder/facilities` | auth | List Registry Facilities | 200, 422 |
| POST | `/api/v1/test-ladder/recommend` | auth | Recommend Test Ladder | 200, 422 |

## Treatment Continuity & Radiotherapy (M7)

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/api/v1/continuity/courses` | auth | List Radiotherapy Courses | 200, 422 |
| POST | `/api/v1/continuity/courses` | auth | Create Radiotherapy Course | 201, 422 |
| GET | `/api/v1/continuity/ledger` | auth | Get Delay Ledger | 200, 422 |
| GET | `/api/v1/continuity/machines` | auth | List Linac Machines | 200, 422 |
| POST | `/api/v1/continuity/machines/{id}/status` | auth | Update Machine Status | 200, 422 |
| GET | `/api/v1/continuity/patients/{id}/delay-notice` | auth | Get Patient Delay Notice | 200, 422 |
| POST | `/api/v1/continuity/schedule/confirm` | auth | Confirm Radiotherapy Schedule | 200, 422 |
| POST | `/api/v1/continuity/schedule/solve` | auth | Solve Radiotherapy Schedule | 200, 422 |

## untagged

| Method | Path | Access | Summary | Responses |
|---|---|---|---|---|
| GET | `/` | public | Root | 200 |
| GET | `/health` | public | Health Check | 200 |
| GET | `/live` | public | Live | 200 |
| GET | `/metrics` | token | Metrics | 200 |
| GET | `/ready` | public | Ready | 200 |

*66 operations.*
