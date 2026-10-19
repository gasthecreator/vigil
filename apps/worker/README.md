# `apps/worker`

Thin entrypoint for the Vigil reminder / outbox worker (G-12).

The poller implementation remains in `apps/api/vigil_api/worker.py` (ADR-0009).
This package exists so the monorepo layout in ADR-0001 is honest: operators and
`infra/Dockerfile.worker` can target `apps/worker` without a second copy of the
queue logic. See `docs/adr/0031-worker-and-vigil-opt-layout.md`.

```bash
# From a workspace with vigil-api installed:
PYTHONPATH=apps/api python -m worker --interval 30
# Equivalent legacy form (still supported):
PYTHONPATH=apps/api python -m vigil_api.worker --interval 30
```
