# Runbook: Worker / outbox queue backlog

**Alert:** Oldest pending outbox/reminder task age exceeds SLO (5 minutes) or worker process down.  
**Related:** ADR-0009, `apps/api/vigil_api/worker.py`, `apps/worker/`, SLO “Outbox backlog”.

## Immediate
1. Check worker container/process: `docker compose -f infra/docker-compose.yml ps worker`.
2. Check API `/ready` (worker shares DB).

## Diagnose
1. Tail worker logs for crash loops, DB lock errors, or poison messages.
2. Count pending rows in the outbox / reminder tables (SQL appropriate to the schema in use).
3. Confirm interval flag (`--interval`) was not raised accidentally.

## Recover
1. Restart worker only after confirming DB is healthy.
2. For a poison task: quarantine by task id (do not delete audit-relevant rows); file a bug with the payload shape.
3. Scale vertically first on single-node deployments; multi-worker requires lease semantics (not claimed here).

## Verify
Backlog age returns under SLO; no duplicate side-effects on reminders already sent.
