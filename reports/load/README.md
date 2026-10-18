# reports/load

`LOAD_TEST_HTTP_RESULTS.*` and `SOAK_TEST_HTTP_RESULTS.*` are the current results (real HTTP, written only by `scripts/run_load_test.py` / `scripts/run_soak_test.py`).

`LOAD_TEST_RESULTS.*` and `SOAK_TEST_RESULTS.*` are the Phase 8b results: **in-process** `TestClient` runs (150 requests at concurrency 5; 5 s and 305 requests, peak RSS). They are kept byte-for-byte because `docs/release/RELEASE_MANIFEST_v1.0.0-rc.1.json` lists them, but they do not support any claim about HTTP latency under concurrency or memory stability (see `docs/progress/PHASE-8B-REPORT.md` errata E3).
