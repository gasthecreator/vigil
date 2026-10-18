# ADR 0023: A declared route policy checked against the running server, and one shared bad-news gate

## Status
Accepted as an engineering decision.

## Context
Two defects of the same kind were found while building silent mode: a safety control (or an access rule) enforced on the route that was tested and missing on its siblings.
- `tests/security/test_penetration_suite.py` holds a policy table for every route but exercises eleven routes. Calling all routes as all roles showed `POST /patients/`, `/baseline` and `/labs` open to any authenticated role (and `/labs` without a consent check, which remains), `shares` open to caregivers, and several roles outside the intended set on `second-look`, `symptoms` and `disclosure/request-release`.
- Hazard H17 (premature disclosure of bad news) was tested on the explainer routes only. `GET /patients/{id}`, `/risk-history`, `/trajectory`, `/observations` and `GET /alerts/stream` returned withheld results to patient and caregiver tokens.

## Decision
1. **`vigil_api/route_policy.py`** declares, per route, the allowed roles and the silent-mode behaviour. It is written by hand, not generated from the code, so that it can disagree with the code. `tests/security/test_route_policy_full_matrix.py` calls every route as each role, as an unknown role and with no token (valid bodies where the handler decides authorization after validation) and fails on any disagreement; a second test shows the coverage check fails when a route lacks an entry.
2. **Role gates were added (and a consent check on `/baseline`)** where the table says the code was too open (`create_patient`, baseline, labs, symptoms, shares, second-look, disclosure request). Where the code was the better reading (for example `alerts/acknowledge` admits `quality_lead`, not `admin`) the table follows the code and the older penetration-suite table is reported as inaccurate in `docs/proposals/PROP-0004-penetration-suite-policy-table.md`; that file is not edited.
3. **`vigil_api/disclosure.py`** holds the bad-news gate (`withheld_for(db, patient, user)`) used by every patient-facing route. While a patient's escalate-level or high-tier result is unreleased, patient and caregiver tokens get 403 `disclosure_locked` on risk-history and trajectory, null risk fields on `GET /patients/{id}`, no quality flags on observations, and no events on the alert stream. Clinical staff are unaffected. The test drives the state and calls every sibling route as the patient and as a caregiver, before and after a clinician releases the result, and was shown to fail without the fix.

**Not done, on purpose:** the consent check on `/labs`. It made the overseer-owned `tests/acceptance_p5` test `test_legacy_lab_endpoint_cannot_bypass_the_no_dismissal_pipeline` fail (that test posts a draw for a patient with no consent record), acceptance tests are read-only for the executor, and so the gap is recorded as hazard H25 with a strict-xfail test and `docs/proposals/PROP-0005-labs-route-consent.md`.

## Consequences
- Behaviour change: patient and caregiver roles lose `POST /patients/`, `/baseline` and `/labs`, quality_lead loses the same three, and caregivers lose the share routes; nurse_clerk and quality_lead lose access to the share, second-look and disclosure-request routes, and quality_lead loses `POST symptoms`.
- The gate uses "any unreleased escalate or high-tier result", which is stricter than the companion summary's "latest result" rule; the two are consistent for the safe direction (the patient route may withhold when the companion view shows).
- `docs/safety/HAZARD_LOG.md`: H17 gains the sibling routes and its history; new H23 (silent-mode exposure) and H24 (write-role gaps).
