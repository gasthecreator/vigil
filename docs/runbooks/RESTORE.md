# Runbook: Restore from backup

**Alert:** API `/ready` failing after host loss, or operator-initiated DR drill.  
**Related:** [`BACKUP_AND_RESTORE.md`](BACKUP_AND_RESTORE.md), [`../resilience/DISASTER_RECOVERY.md`](../resilience/DISASTER_RECOVERY.md), SLO row “API ready”.

## Immediate
1. Confirm blast radius: single node vs storage vs region.
2. Do **not** start a second writer against a partially restored volume.

## Restore
1. Stop API and worker: `docker compose -f infra/docker-compose.yml stop api worker`.
2. Restore Postgres dump or SQLite `.backup` per `BACKUP_AND_RESTORE.md`.
3. Restore audit anchor file (`VIGIL_AUDIT_ANCHOR_PATH`) next to the DB restore.
4. Start services; wait for `GET /ready` → 200.
5. Run audit-chain verification (see `AUDIT_CHAIN_BREAK.md`).

## Verify
- `curl -sf localhost:8000/ready`
- Spot-check one consented patient timeline in the workstation (synthetic or partner sandbox only).

## Escalate
If RPO/RTO targets in `BACKUP_AND_RESTORE.md` are missed, record the miss in the incident notes; do not reword the target.
