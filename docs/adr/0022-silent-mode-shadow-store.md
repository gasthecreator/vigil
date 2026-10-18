# ADR 0022: Silent mode writes model output to a separate shadow database, enforced on the server

## Status
Accepted as an engineering decision. The monitoring definitions in `docs/clinical/SILENT-MODE.md` section 5 need clinical-statistical review at ratification of `PREREGISTRATION.md`.

## Context
`PREREGISTRATION.md` section 6 requires a silent mode whose alerts "no clinician-facing route can read". Two properties make this hard: model output reaches clinicians through many routes (six ingestion routes return or store alerts, tasks and risk records, and a dozen read routes list them), and a flag that is only checked in the UI would repeat the P6B failure ("bad-news mode is UI-only").

## Decision
1. **A separate database, not a column.** `vigil_api/shadow_store.py` has its own engine, declarative base and session factory. The clinician-facing ORM session cannot see its tables, and an injected statement through it cannot reach them (tested).
2. **Divert at the source.** In `ingest_single_observation_internal` the model outputs are written to the shadow store *instead of* the clinical database, and the function returns `None` for risk, alert and task. Nothing derived from the model is stored where a read route could list it, so no read route needs a filter that could be forgotten. K2 detector state is also kept in the shadow store.
3. **Server setting only.** `VIGIL_SILENT_MODE` and `VIGIL_SILENT_SHADOW_DATABASE_URL`; the server refuses to start with silent mode on and no distinct shadow URL, and refuses requests (HTTP 503) if the store is unusable. No request input is read.
4. **Routes whose response is a model output are blocked (409)**: baseline entry, what-if simulation, demo seeding.
5. **Structure is tested.** An AST test fails if any module under `vigil_api/api/` imports the shadow store or the monitor, or uses an undeclared attribute of `silent_mode`; the facade has no function returning predictions. A test that scans every GET route as every role fails if any shadow value appears (and is shown to fail when silent mode is off).
6. **Monitoring reads only the shadow store**, from an operator script, never an HTTP route.

## Consequences
- `ObservationCreateResponse.risk_assessment` became optional and gained `outputs_withheld`; `docs/api/openapi.json` was regenerated.
- The audit record of an ingestion in silent mode omits the adjudicated action and alert flag.
- Orphans (observation without prediction or the reverse) are possible on a crash between the two commits and are documented, not prevented. A distributed transaction was rejected as disproportionate for a monitoring store.
- Same-process access remains: a person with both database credentials can read both. This is an operational control, listed in `docs/HANDOVER.md`.
- The score monitored for the M3/K2 pipeline is M3's probability that a change is real, not a recurrence probability (`score_kind`); `PREREGISTRATION.md` section 6 is silent on this and the report states it.
