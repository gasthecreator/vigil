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

## Test conflict found and repaired

`apps/api/tests/test_api_endpoints.py` and
`apps/api/tests/test_e2e_simulation.py` required abnormal synthetic labs to
produce “ACTIONABLE ALERT” responses and triage flags. They asserted behaviour
from the quarantined heuristic. These ordinary tests have now been replaced
with checks for explicit abstention, preserved lab recording, and hidden
historical output. Overseer-owned acceptance tests were not changed.

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

## Implementation evidence (Q-7 work in progress)

Source evidence: `apps/api/vigil_api/ml/inference.py`,
`apps/api/vigil_api/api/endpoints/patients.py`,
`apps/api/vigil_api/api/endpoints/analytics.py`,
`apps/api/vigil_api/schemas/inference.py`, and
`apps/api/vigil_api/models/v2.py::RiskInference`. This proposal is not model
validation or clinical evidence.

The API repair now makes both legacy `VigilEngine` prediction methods fail
closed; records lab data without creating new `RiskInference` rows; returns
explicit unavailable/abstained contracts; and hides historical heuristic scores
from detail, trajectory, and triage. The triage queue now orders recorded active
tasks by their stored escalation and due dates. Cohort analytics returns null
for unsupported risk metrics. The E12-derived M1 prior is also quarantined;
baseline pathology fields remain stored and its vector column is nullable through
Alembic migration `b2c3d4e5f6a9`. Historical risk rows remain stored and are
still considered by the disclosure lock as a conservative hold.

The full API suite passes locally (229 passed, 2 skipped); the focused queue,
silent-mode, disclosure, migration and contract-generator suite passes (60
passed); and the enabled P5/P15 acceptance tests pass (7 passed). The initial
sandboxed repository suite reported 919 passed, 18 skipped, 7 failed, and 3
errors. Four load/resilience failures were caused by denied loopback socket
binds; `tests/resilience/test_load_and_soak.py` passed all 9 tests when rerun
with loopback access. The full repository suite then passed 925 tests and
skipped 18, with four failures. Those failures are unchanged scientific gates:
K3 shuffled-outcome/joint-model canaries, the B1/GBM baseline score floor, and
G1 calibration. They remain open and are not claimed as fixed by this API
change. These checks do not validate M3/K2 performance, establish the
statistical validity of other model routes, or close Q-7 packages B, F, or H.
Repository CI and the broader source-to-claim audit remain open.
