# P16 PR1 report — production reality (G-01, G-02, G-03)

> Status: SUBMITTED FOR REVIEW. Maturity stays L0. Overseer audit files and acceptance tests untouched.

## Outcome
`infra/` holds digest-pinned, multi-stage, non-root Dockerfiles for api/web/worker and a healthchecked compose file (postgres + api + worker + web). The API depends on `psycopg`, Alembic upgrade/downgrade is exercised on Postgres in CI, API/security fixtures honour `VIGIL_POSTGRES_TEST_URL`, and a scale probe writes `reports/perf/SCALE_TEST_RESULTS.json` with honest cohort size (full §9.5 size may be missed — budgets are not reworded).

## Evidence
| Gap | Artefact |
|---|---|
| G-01 | `infra/Dockerfile.{api,web,worker}`, `infra/docker-compose.yml`, `infra/.env.compose.example`, `tests/deployment/test_on_prem_install.py::test_compose_stack_files_exist_and_are_non_root` |
| G-02 | `psycopg` in `apps/api`, `apps/api/tests/test_migrations_postgres.py`, `.github/workflows/postgres-and-images.yml`, conftest/security Postgres path |
| G-03 | `apps/api/alembic/versions/c9d0e1f2a3b4_009_scale_indexes.py`, `scripts/run_scale_test_postgres.py`, `reports/perf/SCALE_TEST_RESULTS.json` |

## Deviations / honesty
1. Local Docker daemon was unavailable when writing this branch; image **builds** are gated in CI (`docker-build` job).
2. Acceptance suites still hard-code SQLite fixtures (overseer-owned) → `docs/proposals/PROP-0006-acceptance-postgres-fixtures.md`.
3. Scale probe default size is below 1e5×1e7; the JSON records `plan_size_reached: false` and leaves plan budgets unchanged.

## Gate that can fail
CI step “Seeded failure — alembic against … bad host” expects non-zero exit before the real upgrade path runs.
