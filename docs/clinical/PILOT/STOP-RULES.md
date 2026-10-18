# Pilot stop rules

> **Status: DRAFT-UNREVIEWED.** Numbers marked PROPOSED have no clinical ratification. This document governs the silent-mode period (tier T-Q) and any later live pilot (tier T-L). It is referenced by `docs/clinical/PREREGISTRATION.md` section 6. Vigil is decision support; it never replaces the routine follow-up a patient is already due, so stopping Vigil never stops care.

## 1. What "stop" means
| Level | Meaning | How |
|---|---|---|
| **Pause evaluation** | Keep collecting, stop interpreting; no analysis result is released until the review closes | Operator marks the monitoring report as breached and informs the clinical lead (section 4) |
| **Return to silent** | Outputs stop reaching clinicians; data capture continues | Set `VIGIL_SILENT_MODE=true` with a separate `VIGIL_SILENT_SHADOW_DATABASE_URL` and restart the API; verify with `apps/api/tests/test_silent_mode.py` and a manual ingestion (response has `outputs_withheld: true`) |
| **Full stop** | Vigil is taken out of the workflow | Stop the API service and the web tier; clinicians use the pre-existing process; data kept, not deleted |

## 2. Automatic triggers (the on-call operator acts on the first of these; no discussion needed)
| ID | Trigger | Level | Source |
|---|---|---|---|
| S-01 | Any monitoring breach: alarm rate (lower bound above PR-04), calibration slope interval wholly outside [PR-01, PR-02], conformal coverage short of nominal by more than PR-09, an analyte's missingness or refused-ingestion rate more than double its first window | Pause evaluation | `scripts/silent_mode_ctl.py report` exit code 3 |
| S-02 | A patient or caregiver is shown a withheld escalate-level result (any route) | Return to silent, then incident S1 | Incident report from a patient, caregiver or clinician; operator review |
| S-03 | The audit chain fails verification | Full stop until explained | `GET /api/v1/audit/verify` returns `valid: false` |
| S-04 | An implausible or wrong-unit value is accepted into the record, or an observation is attributed to the wrong patient | Return to silent | Incident report; hazard H4 |
| S-05 | Data of a patient without active consent is processed or shown | Return to silent | Incident report; hazard H21 |
| S-06 | Silent mode found off while the protocol says on, or shadow data readable by a clinical user | Return to silent immediately, incident S1 | Operator check; hazard H23 |
| S-07 | The shadow store is unavailable (HTTP 503 on ingestion) for longer than PROPOSED **4 hours** | Operator escalates to the data steward; evaluation window flagged incomplete | API logs |
| S-08 | Any unresolved incident of severity S1, or two of severity S2 in 30 days | Pause evaluation until the review closes | Incident register |

## 3. Review triggers (a human decides within PROPOSED 2 working days)
- Alert acknowledgement without a recorded disposition is impossible by design; if a clinician reports being unable to record a *true* disposition, that is a review trigger.
- A clinician reports that the alerts were never looked at, or that they changed care on the basis of a silent-mode output (the protocol says they cannot see one).
- The rejection rate of the partner extraction exceeds PR-07 on a refresh.
- A model, parameter, threshold or feature definition is changed after the freeze: that is a protocol deviation and stops confirmatory analysis until recorded.

## 4. Who decides (names to be filled by the owner; none are filled today)
| Role | Person | Authority |
|---|---|---|
| Clinical lead | [OWNER TO NAME] | Ends a pause; decides review outcomes; owns PR-01 to PR-09 |
| Data steward | [OWNER TO NAME] | Controls the shadow store and outcome imports; reconciles observations and predictions |
| Operator on call | [OWNER TO NAME] | Executes section 1 at any trigger in section 2 without waiting |
| Statistician | [OWNER TO NAME] | Interprets monitoring reports; rules on open definitions in `docs/clinical/SILENT-MODE.md` section 5 |

## 5. Restart
A stop is lifted only by the clinical lead in writing, after an incident report (`INCIDENT-TEMPLATE.md`) names the cause and the correcting change, and the test that now catches it is in the repository and passing. A parameter is never changed to make a breach disappear.

## 6. What these rules do not do
They do not make the system safe by themselves, do not set clinical thresholds, and do not replace an ethics approval or a regulator's requirements (`docs/HANDOVER.md`, H-001 and H-003).
