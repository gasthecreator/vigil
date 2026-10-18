# Vigil API load test (real HTTP)

> Written by `scripts/run_load_test.py`. Do not edit by hand.

- Date (UTC): 2026-10-18T08:17:31Z
- Transport: **http** to a separate `uvicorn` process (1 worker), staging profile with authentication, SQLite file database, no TLS
- Host: macOS-26.6.2-arm64-arm-64bit, 8 CPUs, Python 3.12.15
- Workload: 2000 requests, concurrency 10, 8.92 s, 224.27 req/s; mix = reads of patients/triage/continuity plus POSTs through the lab-ingestion pipeline (audit chain, M3/K2/M5)

## Budgets

| Metric | Measured | Budget | Verdict |
|---|---|---|---|
| p95 latency (all requests; target from the Phase 8b claim, not MASTER_PLAN) | 202.55 ms | <= 200.0 ms | FAIL |
| error rate | 0.0 % | <= 0.1 % | PASS |
| triage queue p95 (MASTER_PLAN §9.5: < 400 ms at 10^5 patients/PostgreSQL; here 10 patients/SQLite) | 44.41 ms | < 400.0 ms | PASS |

Latency: p50 22.85 ms, p90 178.52 ms, p95 202.55 ms, p99 239.28 ms, max 303.01 ms.

## Per endpoint

| Endpoint | n | p50 | p95 | p99 | status codes |
|---|---|---|---|---|---|
| `/api/v1/continuity/courses` | 286 | 8.78 | 13.64 | 19.41 | {'200': 286} |
| `/api/v1/continuity/machines` | 286 | 9.84 | 15.41 | 23.94 | {'200': 286} |
| `/api/v1/patients/` | 429 | 24.41 | 41.57 | 81.68 | {'200': 429} |
| `/api/v1/patients/triage` | 429 | 34.35 | 44.41 | 49.64 | {'200': 429} |
| `/api/v1/patients/{id}/labs` | 284 | 193.01 | 245.16 | 294.02 | {'200': 284} |
| `/health` | 286 | 4.69 | 6.99 | 10.04 | {'200': 286} |

## Limits of this measurement

One host runs both client and server, so client and server compete for CPU; one uvicorn worker; SQLite; no TLS or reverse proxy; synthetic data; 10 patients. It says nothing about hospital hardware, PostgreSQL, WAN latency or multi-worker behaviour.
