# PROP-0007: Extend acceptance P14 public allowlist for G-09 probes

**Status:** OPEN (acceptance tests are overseer-owned; executor must not edit them)  
**Related:** G-09, `tests/acceptance_p14/test_p14_contract.py`, PROMPT-P16 PR3

## Problem
G-09 requires unauthenticated `GET /live`, `GET /ready`, and `GET /metrics` for orchestrator probes and Prometheus scrapes. `tests/acceptance_p14` only permits unauthenticated success for `PUBLIC_EXACT = {"/", "/health"}` and companion share-token prefixes. Adding the new routes to OpenAPI without updating that allowlist fails P14.

## What the executor shipped (this PR)
- Endpoints exist and work (`apps/api/vigil_api/main.py`, `observability.py`).
- They use `include_in_schema=False` so OpenAPI enumeration (and therefore P14) does not see them.
- Behaviour is covered by `apps/api/tests/test_observability_probes.py` and documented in `docs/operations/SLOS.md`.

## Requested overseer change
1. Add `"/live"`, `"/ready"`, `"/metrics"` to `PUBLIC_EXACT` in `tests/acceptance_p14/test_p14_contract.py`.
2. Executor will then set `include_in_schema=True`, add `ROUTE_POLICY` / `OPENAPI_RBAC_POLICY` public entries, and regenerate `docs/api/openapi.json`.

## Why not a workaround forever
Hiding ops probes from OpenAPI is temporary honesty about the acceptance gate, not the desired long-term contract.
