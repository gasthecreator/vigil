# Silent mode (tier T-Q): what it does, how to run it, how to read its report

> **Status: DRAFT-UNREVIEWED.** Describes `apps/api/vigil_api/silent_mode.py`, `shadow_store.py`, `silent_monitoring.py` and `scripts/silent_mode_ctl.py` as they are. The monitoring thresholds are the PROPOSED parameters of `PREREGISTRATION.md` section 7 until a named ratifier freezes them. Nothing here is a validation result.

## 1. Purpose
Silent mode runs the real pipeline on real incoming data while **no model output is shown to anyone caring for the patient**. Outputs are kept so that, later, they can be compared with what actually happened (prospective, outcome-blind to the clinicians).

## 2. What changes when `VIGIL_SILENT_MODE=true`
Set only in the server environment together with `VIGIL_SILENT_SHADOW_DATABASE_URL` (a database that is **not** the clinical one; the server refuses to start otherwise, and refuses requests with HTTP 503 if the store becomes unusable).

| Route family | Silent-mode behaviour |
|---|---|
| Ingestion: `POST /patients/{id}/observations`, `/patients/{id}/labs`, `/observations/batch-import`, `/hl7/oru-r01`, `POST /fhir/Observation`, `/sync/batch` | The observation is stored in the clinical database as usual (data is data) and all unit/plausibility checks still reject bad input (hazard H4). M3 adjudication, the K2 detector and the would-be alert are computed and written to the shadow store. The clinical database receives **no** risk assessment, alert, follow-up task, legacy risk inference or detector state. The response carries `outputs_withheld: true`, `risk_assessment: null` and `adjudicated_action: "withheld_silent_mode"` (the legacy labs route answers 202). The audit record carries no model output. |
| `POST /patients/{id}/baseline`, `POST /patients/{id}/simulate`, `POST /analytics/seed-demo-cohort` | HTTP 409 `silent_mode_blocked`: their response is itself a model output. |
| All reads | Unchanged. Because nothing was written, nothing from the silent period can appear in an alert list, triage queue, trajectory, risk history, explainer, companion view, follow-up outreach, analytics or audit listing. Results created *before* silent mode was switched on remain visible. |

No request body field, header or query parameter changes any of this (tested with forged bodies, headers and query strings). No route reads, toggles or lists the shadow store.

## 3. What is recorded (shadow store tables)
`shadow_predictions` (one row per accepted observation: patient and observation ids, analyte, specimen time, score and `score_kind`, M3 action and probabilities, K2 log e-value/tier/alert, would-alert flag and alert type, plausibility status, model versions, input hash, optional conformal set), `shadow_detector_states` (K2 state per patient), `shadow_ingest_rejections` (counts of unit and unregistered-analyte refusals, no values), `shadow_outcomes` (imported by the data steward).

**What the score is.** For the M3/K2 pipeline `score` is M3's probability that a measured change is real (`score_kind = m3_p_real`). It is not a probability of recurrence. The calibration monitor therefore asks how well *that quantity* tracks recurrence within 365 days; the report says so in its caveats. If a recurrence-risk model replaces M3/K2, it must write its own `score_kind`.

## 4. Operating it
```bash
# 1. outcomes from the chart (CSV: patient_id,event_type,event_time; event_type in recurrence_confirmed|last_followup|death_other)
uv run python scripts/silent_mode_ctl.py import-outcomes --csv outcomes.csv          # shadow URL from VIGIL_SILENT_SHADOW_DATABASE_URL
# 2. the monitoring report (refused unless the pre-registration is frozen)
uv run python scripts/silent_mode_ctl.py report --out reports/silent/$(date +%F)
# rehearsal on unratified parameters (PR-04 has no default and must be given):
uv run python scripts/silent_mode_ctl.py report --out /tmp/rehearsal --synthetic-dry-run --alert-budget 20
```
Exit codes of `report`: 0 no breach and everything evaluable; **3 breach**; 4 pre-registration not frozen; 5 no breach but some monitor could not be evaluated (for example PR-04 not ratified).

## 5. The four monitors and how they are defined
Definitions are printed in the module docstring of `silent_monitoring.py` and apply exactly as written; where `PREREGISTRATION.md` leaves a choice open the choice is listed here for the clinical statistician to rule on at ratification.

1. **Alarm rate.** Alerts per 100 patient-months, one alert per patient-day (landmark) at most, exposure from first to last specimen per patient (a patient with one specimen contributes none, which overstates the rate slightly), exact Poisson (Garwood) 95 % interval. Breach if the lower bound exceeds PR-04. With no ratified PR-04 the status is `NOT_EVALUABLE`; there is no default.
2. **Calibration drift.** Consecutive non-overlapping blocks of determinable landmarks, each closed at PR-08 events; logistic calibration slope with a Wald 95 % interval and the observed/expected ratio. Breach if the interval lies wholly outside [PR-01, PR-02] (a literal reading of "excludes"; an interval straddling a bound is reported as inconclusive, not as a breach). A landmark is determinable when a recurrence is confirmed within 365 days, or follow-up reaches 365 days without one; death from another cause before then excludes it (competing risk not modelled).
3. **Conformal coverage.** Only if the producing model records conformal sets. The M3/K2 pipeline does not, so the report says `NOT_MEASURABLE` rather than inventing a coverage.
4. **Data shift.** Per-analyte missingness (blocks of PR-08 landmark-days) and refused-ingestion rate (blocks of PR-08 attempts), each against the first block; breach if a later block exceeds twice the first. If the first block's rate is zero the ratio is undefined and this is reported, not declared a breach.

A breach pauses further evaluation and starts the review in `PILOT/STOP-RULES.md`. It is not resolved by editing a parameter.

## 6. Limits that are not hidden
- The shadow store is written by the same process as the clinical database. It is a separate database, kept out of reach of clinician-facing code by structure and tests, but a person with access to both databases can read both. Separate database credentials and an access review are owner/operator actions (`docs/HANDOVER.md`).
- A crash between the clinical commit and the shadow write, or the reverse, can leave an observation without a prediction or a prediction without an observation. The shadow store cannot detect the first case (the monitor reads only the shadow store). A periodic reconciliation by an operator with access to both is recommended and not automated.
- Silent mode proves nothing about clinical benefit; it only collects what the model would have said.
- Everything above is tested on synthetic data and temporary databases. No real patient has passed through it.
