# Runbook: Migration rollback

**Alert:** Alembic upgrade failed mid-way, or post-deploy `/ready` fails after schema change.  
**Related:** G-02 Postgres migrations, SLO “Migration rollback”.

## Immediate
1. Stop API/worker writers.
2. Do not run ad-hoc SQL “fixes” that bypass Alembic revision history.

## Rollback
1. Identify current and previous revisions: `alembic current`, `alembic history`.
2. `alembic downgrade -1` (or to the last known-good revision) on the **same** database URL used by the failed deploy.
3. If downgrade is impossible (destructive upgrade): restore from backup (`RESTORE.md`) to the pre-upgrade snapshot.

## Verify
1. `alembic current` matches the intended revision.
2. `GET /ready` → 200.
3. Run a smoke subset: health, one authenticated patient list, one migration-sensitive acceptance if available.

## Notes
Never claim a migration is reversible without a tested downgrade path in CI (Postgres service container).
