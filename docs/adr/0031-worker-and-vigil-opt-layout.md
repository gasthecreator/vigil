---
status: accepted
date: 2026-10-19
decision-makers: Executor (PROMPT-P16 PR3)
consulted: ADR-0001, ADR-0009, ADR-0019
informed: Contributors
---

# 0031. `apps/worker` shim and deferred `packages/vigil-opt`

## Context
ADR-0001 lists `apps/worker` and `packages/vigil-opt` as first-class layout targets. As of P16 PR3:

- The background outbox/reminder poller lives in `apps/api/vigil_api/worker.py` (ADR-0009) and is the `CMD` of `infra/Dockerfile.worker`.
- Radiotherapy scheduling (M7 urgency ranking + CP-SAT research) lives in `packages/vigil-ml/vigil_ml/scheduler.py` and `scheduler_research.py` (ADR-0019). There is no separate optimiser package.

PROMPT-P16 G-12: implement the split if cheap, otherwise record the deviation.

## Decision
1. **`apps/worker` exists as a thin entrypoint** (`python -m worker` → `vigil_api.worker`). No second copy of queue logic. Docker continues to call `python -m vigil_api.worker` (same code path; image does not need a separate wheel).
2. **`packages/vigil-opt` is deferred.** Moving the scheduler out of `vigil-ml` would force a workspace member, import-linter contract rewrite, and API import churn for no runtime behaviour change. The optimiser remains in `vigil-ml` until a clean boundary (pure CP-SAT + ranking, no torch) is justified by a real second consumer.
3. README layout diagrams that still list `vigil-opt` as present must describe it as **planned / deferred (this ADR)**, not as a shipping package.

## Consequences
- Gap G-12 is **DECIDED-BY-ADR** (worker shim shipped; vigil-opt deviation recorded).
- A future PR that extracts `vigil-opt` must update ADR-0001 confirmation, import-linter contracts, and this ADR's status.
