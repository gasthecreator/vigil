# Go / no-go checklist for entering silent mode (T-Q) and for a later live pilot (T-L)

> **Status: DRAFT-UNREVIEWED.** This file records what is true at the commit that contains it. A row is "MET" only when its evidence is a test or file that exists and passes in CI at that commit; every human step stays "NOT MET" until a named person records it. **Today the answer to both gates is NO-GO.**
> Evidence names below were checked against the repository when this file was written (`grep` for the test names). Re-check them with `python scripts/verify_hazard_log.py` and the test commands shown.

## Gate A: silent mode (T-Q)
| # | Condition | Evidence | Status |
|---|---|---|---|
| A1 | Ethics approval for prospective collection | Approval letter (outside the repository) | NOT MET (human, H-001) |
| A2 | Data-sharing / processing agreement with the site | Signed agreement | NOT MET (human) |
| A3 | `PREREGISTRATION.md` frozen with ratified PR-01 to PR-09, bootstrap seed and partition key id | `python scripts/check_prereg_freeze.py` exits 0 | NOT MET (no `PREREG-FREEZE.json`) |
| A4 | Silent mode diverts outputs on every ingestion route and fails closed | `apps/api/tests/test_silent_mode.py::test_ingestion_diverts_outputs_to_the_shadow_store`, `::test_ingestion_fails_closed_without_a_separate_shadow_store`, `::test_settings_refuse_unsafe_silent_configuration` | MET (automated, synthetic data) |
| A5 | No shadow value readable through any GET route as any role; forged requests cannot disable silent mode | `::test_no_get_route_returns_a_shadow_value_as_any_role`, `::test_forged_requests_cannot_disable_silent_mode`, `::test_only_the_write_facade_and_the_monitor_import_the_shadow_store` | MET (automated) |
| A6 | Separate database credentials for the shadow store; access list reviewed | Operator record | NOT MET (human; no deployment exists) |
| A7 | Monitoring report runs on the deployment and its exit code reaches the on-call person | `scripts/silent_mode_ctl.py report` run on the deployment; alert routing configured | NOT MET (no deployment) |
| A8 | Authorization policy checked for every route and role | `tests/security/test_route_policy_full_matrix.py` | MET (automated) |
| A9 | Bad news withheld on every patient-facing route | `apps/api/tests/test_bad_news_sibling_routes.py` | MET (automated) |
| A10 | Stop rules read and accepted; named people filled in `STOP-RULES.md` section 4 | Signed copy | NOT MET (human) |
| A11 | Staff trained and competency recorded | `TRAINING.md` section 5 records | NOT MET (human) |
| A12 | Incident process rehearsed once with a synthetic incident | Filled `INCIDENT-TEMPLATE.md` | NOT MET (human) |
| A13 | Backup and restore tested on the deployment | `docs/runbooks/` procedure run, result recorded | NOT MET (procedure tested locally; not on a deployment) |
| A14 | Partner-extraction ingestion passes on the site's own de-identified sample | `scripts/run_partner_ingest.py` report | NOT MET (needs the site's data) |
| A15 | Production secrets, TLS and authentication provisioned; no default secret | Deployment record; `tests/acceptance_p5/test_api_security.py::test_default_jwt_secret_is_not_accepted_in_production` | NOT MET (no deployment); the test part is MET |
| A17 | Consent enforced on every route that ingests patient data | `apps/api/tests/test_labs_consent_gap.py` (the two xfail tests must pass without their markers); `docs/proposals/PROP-0005-labs-route-consent.md` | NOT MET (legacy `/labs` does not check consent; hazard H25 OPEN) |
| A16 | Web tier vulnerability policy met | `cd apps/web && npm audit --omit=dev` | NOT MET (X-DEP-1 in `docs/HANDOVER.md`) |

## Gate B: live pilot (T-L), additionally
| # | Condition | Evidence | Status |
|---|---|---|---|
| B1 | A completed silent-mode period with its monitoring reports reviewed by the clinical lead | Reports, review minutes | NOT MET |
| B2 | Retrospective validation reported under the frozen protocol | `reports/clinical/` real-data run | NOT MET (needs partner data) |
| B3 | Usability summative testing (IEC 62366-1) with real users | `docs/usability/USABILITY_TEST_PROTOCOL.md` executed | NOT MET (H-005) |
| B4 | Regulatory position agreed with the regulator | Written record | NOT MET (H-003) |
| B5 | Hazard log has no OPEN hazard without an accepted residual-risk decision by the clinical lead | `docs/safety/HAZARD_LOG.md` (H10, H16, H25 are OPEN today) | NOT MET |
| B6 | Patient/caregiver communication reviewed, translated and tested | `TRAINING.md` section 4 reviewed | NOT MET |
