# Vigil API soak test (real HTTP)

> Written by `scripts/run_soak_test.py`. Do not edit by hand.

- Date (UTC): 2026-10-18T08:12:12Z
- Duration actually run: **1801.07 s** (requested 1800.0 s), concurrency 8, 200 patients, 28819 requests (16.0 req/s)
- Transport: **http** to a separate `uvicorn` process (1 worker), staging profile, SQLite file, no TLS
- Host: macOS-26.6.2-arm64-arm-64bit, 8 CPUs, Python 3.12.15

## Verdicts against budgets fixed before the run

| Metric | Measured | Budget | Verdict |
|---|---|---|---|
| overall p95 | 2907.64 ms | <= 200.0 | FAIL |
| error rate | 0.0 % | <= 0.1 | PASS |
| p95 drift (last vs first quarter after warm-up) | 1818.0 -> 3683.98 ms = 102.64 % | <= 50.0 % | FAIL/UNMEASURABLE |
| server RSS growth (median last vs first quarter after warm-up, 162 samples) | 280.015 -> 322.48 MB = 15.17 % | <= 15.0 % | FAIL/UNMEASURABLE |

RSS is the current resident set of the server process sampled with `ps`; it is not peak RSS.

## Limits

One host runs client and server; one worker; SQLite; no TLS; synthetic data growing a single SQLite file and audit chain for the whole run. A pass is not evidence about hospital hardware or PostgreSQL. Memory 'stability' means growth under the stated threshold over this window, not absence of leaks.
