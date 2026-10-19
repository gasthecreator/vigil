# Flake register (G-13)

A flaky test is a bug with an owner. Quarantine only with an entry here and a linked issue/proposal. Do not silently `xfail` or skip.

| ID | Test | Symptom | Owner | Status | Notes |
|---|---|---|---|---|---|
| F-001 | `tests/resilience/test_worker_resilience.py::test_worker_kill_and_restart_lifecycle` | Timing-dependent: `sleep(0.5)` sometimes saw 0 receipts before SIGTERM | executor (P16 PR2) | **FIXED** | Rewritten to poll for first receipt (timeout) then SIGTERM; restart still uses `--once`. |

## Policy
1. If a test fails intermittently in CI, open a row here the same day.
2. Prefer fixing determinism (poll, inject clocks, `--once`) over raising sleeps.
3. Quarantine (`xfail(strict=False)` or skip) requires an owner name and a removal date ≤ 14 days.
