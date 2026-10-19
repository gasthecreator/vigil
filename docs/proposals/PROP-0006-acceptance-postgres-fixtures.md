# PROP-0006 — Acceptance suites still hard-code SQLite fixtures

**Status:** OPEN (overseer-owned tests)  
**Related:** G-02, PROMPT-P16 PR1

## Observation
`tests/acceptance_*` fixtures build their own `sqlite:///` databases (for example `tests/acceptance_p7/test_p7_contract.py`, `tests/acceptance_p8/...`). The executor must not edit acceptance tests. CI therefore runs those suites under a job that *also* provides a Postgres service, but the suites themselves do not bind to that service.

## What PR1 does prove on Postgres
- Alembic upgrade / one-step downgrade / upgrade (`apps/api/tests/test_migrations_postgres.py` + CI steps)
- API HTTP fixtures when `VIGIL_POSTGRES_TEST_URL` is set (`apps/api/tests/conftest.py`)
- Route-policy matrix fixture when the same env is set
- Scale probe (`scripts/run_scale_test_postgres.py`) writing `reports/perf/SCALE_TEST_RESULTS.json`

## Requested ruling
Optionally teach acceptance fixtures to honour `VIGIL_POSTGRES_TEST_URL` the same way `apps/api/tests/conftest.py` does. Until then, acceptance green on the Postgres CI job means “suite still passes”, not “suite executed against Postgres”.
