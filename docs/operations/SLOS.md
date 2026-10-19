# Service level objectives (G-09)

**Audience:** operators and on-call engineers.  
**Scope:** Vigil API + worker on a single compose/on-prem deployment. Numbers below are **engineering targets for the research prototype**, not clinical guarantees and not partner-validated.

## SLIs

| SLI | How measured | Notes |
|---|---|---|
| API availability | Fraction of successful `GET /ready` probes over 5 minutes | `/live` is process-only; `/ready` includes DB |
| Request latency | `vigil_http_request_duration_seconds` on `/metrics` | Path labels are cardinality-bounded |
| Triage p95 | Script-written `reports/perf/SCALE_TEST_RESULTS.json` | Plan budget §9.5: < 400 ms (measured at the scale the probe reached) |
| Timeline p95 | Same scale report | Plan budget §9.5: < 600 ms |
| Queue freshness | Age of oldest unprocessed outbox row (worker logs / future gauge) | Worker interval default 30 s |
| Audit chain integrity | `verify_audit_chain` / ops scripts | Break → page |
| Silent-mode isolation | Shadow store ≠ clinical DB; clinician routes must not read shadow | Leak → page |

## SLOs (prototype)

| Objective | Target | Alert → runbook |
|---|---|---|
| API ready | ≥ 99% of `/ready` probes succeed over 30 days (single-node) | [`runbooks/RESTORE.md`](../runbooks/RESTORE.md) |
| Audit chain unbroken | 100% of verification jobs pass | [`runbooks/AUDIT_CHAIN_BREAK.md`](../runbooks/AUDIT_CHAIN_BREAK.md) |
| Outbox backlog | Oldest pending task age < 5 minutes under normal load | [`runbooks/QUEUE_BACKLOG.md`](../runbooks/QUEUE_BACKLOG.md) |
| Silent-mode leak | Zero clinician-route reads of shadow predictions | [`runbooks/SILENT_MODE_LEAK.md`](../runbooks/SILENT_MODE_LEAK.md) |
| Consent gate | Zero successful patient-scoped reads without active consent (security suite) | [`runbooks/CONSENT_GATE_FAILURE.md`](../runbooks/CONSENT_GATE_FAILURE.md) |
| Migration rollback | Failed Alembic upgrade leaves DB restorable to prior revision | [`runbooks/MIGRATION_ROLLBACK.md`](../runbooks/MIGRATION_ROLLBACK.md) |

## Probes

| Endpoint | OpenAPI | Purpose |
|---|---|---|
| `GET /live` | excluded until PROP-0007 | Liveness (process up) |
| `GET /ready` | excluded until PROP-0007 | Readiness (DB reachable) |
| `GET /health` | public | Compatibility probe (ML status + DB claim) |
| `GET /metrics` | excluded until PROP-0007 | Prometheus text exposition |

OpenTelemetry: set `VIGIL_OTEL_ENABLED=true` (optional `OTEL_EXPORTER_OTLP_ENDPOINT`). Default is **off**.
