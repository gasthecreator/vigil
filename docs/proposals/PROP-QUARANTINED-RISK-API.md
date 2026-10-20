# Proposal: quarantine the legacy API risk score

## Finding

`apps/api/vigil_api/ml/inference.py::VigilEngine.predict_risk` sets
`is_quarantined = True` but still returns a numeric “metastasis risk”, a triage
flag, and follow-up language. It substitutes unmeasured CA 15-3, ALT, AST, and
WBC values with constants, clips scores to `[0.05, 0.95]`, and uses fixed
thresholds. The patient lab route persists this output as `RiskInference` and
ORs the heuristic flag into triage. The hypothetical simulation route returns
it as projected patient risk; analytics also creates risk records for demo
patients. This does not satisfy the repository's abstention and claims rules.

## Existing test conflict

`apps/api/tests/test_api_endpoints.py` and
`apps/api/tests/test_e2e_simulation.py` currently require abnormal synthetic
labs to produce “ACTIONABLE ALERT” responses and triage flags. Those tests
assert behaviour from the quarantined heuristic. The route response schema and
database model also require a numeric risk and boolean triage value, so this
cannot be safely corrected by adding a guard inside `predict_risk` alone.

## Proposed contract

1. Lab ingestion remains available and records the supplied measurements, but
   does not create a risk inference or triage decision unless an explicitly
   approved, registered model is loaded and passes its runtime contract.
2. Hypothetical prediction returns an explicit unavailable/abstained state;
   it does not fabricate a probability, delta, or follow-up recommendation.
3. Synthetic analytics may generate labelled synthetic observations, but must
   not persist patient-shaped risk outputs or place them in clinician queues.
4. API schemas, database nullability/migrations, UI clients, demo seeders, and
   route tests change together. Existing historical inference rows remain
   labelled as legacy heuristic outputs and are excluded from active triage.
5. Add regressions for missing inputs, quarantined model state, no risk-row
   persistence, no queue contamination, and explicit abstention. Do not weaken
   or edit overseer-owned acceptance tests; if one conflicts, record a separate
   evidence-backed proposal.

## Evidence and limits

Source evidence: `apps/api/vigil_api/ml/inference.py`,
`apps/api/vigil_api/api/endpoints/patients.py` (`create_lab_result`,
`simulate_risk`), `apps/api/vigil_api/api/endpoints/analytics.py`,
`apps/api/vigil_api/schemas/inference.py`, and
`apps/api/vigil_api/models/v2.py::RiskInference`. Current ordinary API tests
explicitly assert the heuristic alert path. This proposal is not a fix, model
validation, or clinical evidence. The affected route/schema/database/UI audit
and implementation remain required in Q-7 packages B, F, and H.
