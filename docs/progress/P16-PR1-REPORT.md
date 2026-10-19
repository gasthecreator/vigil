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

## Overseer revisions (review of PR 70, 2026-10-19)
- Lint error fixed (import order). Compose is now **production by default**: the shipped example selected `ENVIRONMENT=local`, `REQUIRE_AUTH=false` and a default JWT secret; secrets are required, placeholders are refused by the entrypoint, Postgres is published on 127.0.0.1 only, the insecure demo profile is `infra/.env.compose.dev.example` (`tests/deployment/test_on_prem_install.py::test_compose_is_secure_by_default_and_dev_profile_is_separate`).
- Scale: the first probe (2,000 patients) hid a linear cost. Re-run at 2k/10k/30k on Postgres 15 with a realistic seed (assessments, inferences, tasks): triage p95 117 / 339 / 1,283 ms; **budget NOT MET at plan size** (extrapolated about 4.3 s; holds up to about 10,000 patients). Triage now pages (`limit`/`offset`, `X-Total-Count`) and reads plain columns; the SQL-side fix is `docs/proposals/PROP-0007-triage-urgency-in-sql.md`. Files: `reports/perf/SCALE_SCALING.json`, `reports/perf/scale_runs/`.
