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

## How each SLO is verified

| Objective | Verified by | Alert rule |
|---|---|---|
| API ready, error rate, latency | Prometheus metrics + blackbox probe | [`infra/prometheus/alerts.yml`](../../infra/prometheus/alerts.yml) (`VigilApiNotReady`, `VigilApiHighErrorRate`, `VigilApiSlowRequests`) |
| Audit chain unbroken | Scheduled `verify_audit_chain` run by the operator (no metric yet) | None: run on a schedule and page on non-zero exit |
| Outbox backlog | Worker logs; **no honest gauge exists** (pending follow-up tasks legitimately stay pending for days) | None |
| Silent-mode leak, consent gate | Security / acceptance suites in CI (`acceptance_p11`, `acceptance_p15`) | None: these are test-time invariants, not runtime metrics |
| Migration rollback | Postgres migration job in CI | None |

Only the first row is alerting today. The other rows are stated as objectives with a runbook, not as monitored SLIs; turning them into metrics is future work and is not claimed here.

## Probes

| Endpoint | Access | Purpose |
|---|---|---|
| `GET /live` | public | Liveness (process up); no dependency detail |
| `GET /ready` | public | Readiness (DB reachable); 503 with `{"status":"not_ready","database":"unavailable"}` and no error detail |
| `GET /health` | public | Compatibility probe (ML status + DB claim) |
| `GET /metrics` | bearer token (`VIGIL_METRICS_TOKEN`); 403 when unset | Prometheus text exposition |

OpenTelemetry: set `VIGIL_OTEL_ENABLED=true` (optional `OTEL_EXPORTER_OTLP_ENDPOINT`). Default is **off**.
