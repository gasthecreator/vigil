# reports/load

All `*_HTTP_*` files are real-HTTP results (separate `uvicorn` process, `httpx` client over TCP, staging profile with authentication, SQLite file). They are written only by `scripts/run_load_test.py` and `scripts/run_soak_test.py`; nothing in them is typed by hand.

| File | What it is |
|---|---|
| `LOAD_TEST_HTTP_RESULTS.*` | Current load result (2000 requests, concurrency 10, 10 patients), run on the final code. **Verdict is in the file.** |
| `SOAK_TEST_HTTP_RESULTS.*` | Current 30-minute soak (concurrency 8, 200 patients), run on the final code. **Verdict is in the file.** |
| `SOAK_TEST_HTTP_RESULTS_run1_10patients.*` | First 30-minute soak, 10 patients, **before** the audit-append, triage and SQLite fixes. Kept because it found them. The harness did not yet record the patient count (it was 10). |
| `SOAK_TEST_HTTP_RESULTS_run2_200patients_before_triage_aggregation.*` | Second soak, 200 patients, after the audit-append and first triage fixes but before pending tasks were aggregated in SQL. |
| `LOAD_TEST_RESULTS.*`, `SOAK_TEST_RESULTS.*` | Phase 8b in-process `TestClient` runs (150 requests at concurrency 5; 5 s / 305 requests, peak RSS). Kept byte-for-byte because `docs/release/RELEASE_MANIFEST_v1.0.0-rc.1.json` lists them. They support no claim about HTTP latency or memory stability (`docs/progress/PHASE-8B-REPORT.md`, errata E3). |

Why the soak patient count changed from 10 to 200 (a change made after seeing run 1): with 10 patients the run wrote about 2000 observations per patient, which is not a realistic per-patient history, and the unbounded K2 detector state (PROP-0002) dominated. This was a harness design change, disclosed here, and run 1 is still committed and still reads FAIL.

What the runs found and what was done about it is in `docs/progress/TIER0-REPORT.md` (section "Load and soak").

Budgets and their provenance: whole-mix p95 <= 200 ms is the target claimed by the Phase 8b report, **not** a MASTER_PLAN figure; MASTER_PLAN 9.5 states "triage queue p95 < 400 ms" at 10^5 patients on PostgreSQL, which these runs (10 or 200 patients, SQLite) do not measure.
