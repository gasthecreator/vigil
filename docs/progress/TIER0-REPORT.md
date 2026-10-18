# Tier 0 report: closing VERDICT-P8B conditions P15-A to P15-G

> Executor report, status **SUBMITTED FOR REVIEW**. The executor does not set verdicts or the maturity level (still L0: no real-data validation exists). Every number below is copied from a script-written file named next to it. Where a number comes from a terminal session that was not committed it says so.

## 1. Summary table

| Condition | What was asked | State | Evidence |
|---|---|---|---|
| P15-A | M7 ship decision with an ADR | Done. The explainable urgency ranking ships; CP-SAT is opt-in research behind the `unvalidated in simulation` badge and an admin/operator gate. | `docs/adr/0019-m7-ships-explainable-urgency-ranking.md`; `packages/vigil-ml/tests/test_scheduler.py`; `apps/api/tests/test_continuity_api.py` |
| P15-B | Time-boxed CP-SAT research attempt | Done, **not promoted**. The pre-registered criterion computed as MET on the headline harm; the all-in re-evaluation fails. | `experiments/EXP-M7-001/` (`PREREG.md`, `results.json`, `REPORT.md`, `ALLIN_ANALYSIS.md`, `CONCLUSION.md`) |
| P15-C | Correct the Phase 8b report | Done by an errata section and inline SUPERSEDED markers; the original text is not deleted. | `docs/progress/PHASE-8B-REPORT.md` section 0 |
| P15-D | Repo-standards audit that can fail | Done. It scores items from inspection and reports **targets not met** for T1-T4. | `docs/audits/REPO-AUDIT-P15.md`, `reports/audit/REPO_AUDIT.json`, `scripts/audit_repo_standards.py`, `tests/governance/test_audit_repo_standards.py` |
| P15-E | "Hash manifest" naming or real signing | Done both ways: renamed; generate/verify tooling; cosign sign/verify tooling tested against a throwaway key. Signing with the owner's key is **not done** (owner action). | `scripts/generate_release_manifest.py`, `tests/governance/test_release_manifest.py`, `docs/release/SIGNING.md` |
| P15-F | Real-HTTP load test and a soak of at least 30 minutes with committed results | Done and **the results are failing verdicts**; see section 4. | `reports/load/` (`README.md` explains every file) |
| P15-G | Audit-hash compatibility ADR and test | Done. | `docs/adr/0020-audit-hash-scheme-versioning.md`, `tests/resilience/test_audit_hash_compat.py`, `tests/resilience/fixtures/audit_chain_v0_golden.json` |
| (STUBS) | Fix `docs/STUBS.md` | Done: stale rows corrected against the repository. | `docs/STUBS.md` |

## 2. M7 research track (P15-B), plainly

- The PREREG was committed alone (`061da43`) before any code or run. Amendment 1 (`1d455f4`) was written on development seeds, before any frozen run: the simulator let the scheduler see future machine failures; `downtime_visibility="persistence"` removes that for the new study. The committed M7-TWIN CP-SAT numbers (Phase 7b/8b) were produced with that leak and are optimistic for CP-SAT.
- The frozen run (`f7e7d0a`, `experiments/EXP-M7-001/results.json`) computed the section 5 criterion as MET (research beats urgency and FCFS on headline harm in 12/12 cells, 24/24 intervals above zero).
- That headline excludes `unscheduled_harm`. Amendment 2 (`63009ac`) was committed before the all-in analysis existed and says it is post-hoc and written after the decomposition table had been seen. `experiments/EXP-M7-001/ALLIN_ANALYSIS.md` (written by `scripts/analyze_m7_cpsat_v2_allin.py`): research beats urgency and FCFS all-in in 0/12 cells, is significantly worse all-in than some baseline in 10/12, has significantly longer mean wait in 12/12 and significantly worse disparity in 11/12; the strongest baseline on the all-in measure is the urgency ranking in every cell.
- Conclusion (`CONCLUSION.md`): not promoted. A mechanism is stated there only as a hypothesis, because utilisation was not recorded.
- Disclosures: the frozen seeds were also used for the earlier v1 CP-SAT evaluation; planner and evaluator share the harm model; the research arm has no fairness bound; the clinician-flag promotion inside the urgency ranking is not covered by simulation evidence.
- `docs/proposals/PROP-0001-m7-headline-harm-includes-untreated.md` asks the overseer to make all-in harm the primary endpoint for scheduler studies. I did not change the M7-TWIN definition.
- `scripts/verify_study_reproducibility.py` now re-runs two replications of one frozen cell and re-derives `ALLIN_ANALYSIS.json` from `results.json`.

## 3. Things the repo-standards audit and the load test made me fix or file

Found by running the real thing, not by reading code:

| Finding | Fix or filing | Test |
|---|---|---|
| `record_audit_event` loaded the whole audit table twice per write (leaf lookup and event count). Per-request cost grew with history. | O(log N) leaf lookup via the anchor with fallback to the old scan; SQL `count`; index on `audit_events.prev_hash` (migration 007). | `apps/api/tests/test_audit_append_scaling.py` (fails on the old code: 299 rows loaded per append at N=150) |
| Triage queue ran about 6 statements per patient and materialised every pending task. | Constant statements; tasks reduced in SQL; `detector_state` deferred. | `apps/api/tests/test_triage_batched.py` (oracle = verbatim copy of the old body; the statement-count test failed on the old code with 145 statements for 24 patients; the task-materialisation test was written after the change and was not run against the old code) |
| SQLite: concurrent writers returned HTTP 500 "database is locked" and connection resets; a few writers waited seconds. | WAL, 30 s busy timeout, in-process fair write lock. | `apps/api/tests/test_sqlite_write_serialization.py`. **Limit:** the semantic tests pass without the lock (SQLite serialises writers itself); the lock improves fairness and tail latency, which I observed in uncommitted intermediate runs and which no committed test pins. |
| K2 detector state grows without bound (cost per update O(observations per patient)). | **Not fixed** (shared package; needs ADR and downstream re-run). | `docs/proposals/PROP-0002-k2-detector-state-unbounded.md` |
| Roster endpoints are unpaginated; triage has no consent or facility filter in the code I read. | **Not fixed**, policy question. | `docs/proposals/PROP-0003-roster-endpoints-unpaginated.md` |
| `STUDY_M10_MISSED_SIGNALS.md` contained absolute local paths. | Generator now writes repo-relative links; file regenerated by its script. | `scripts/verify_study_reproducibility.py` |
| The audit flagged its own test fixture (a fake private-key literal). | Fixture built at runtime. | `tests/governance/test_audit_repo_standards.py` |
| `restore_backup` failed when the target directory did not exist. | `mkdir(parents=True)`. | `tests/resilience/test_audit_hash_compat.py` |

## 4. Load and soak (P15-F): the committed results do not pass

Written by `scripts/run_load_test.py` and `scripts/run_soak_test.py`; see `reports/load/README.md`.

- **Load** (`LOAD_TEST_HTTP_RESULTS.json`; 2000 requests, concurrency 10, 10 patients, one uvicorn worker, SQLite, same host for client and server): error rate 0.0 % (PASS); triage p95 44.41 ms against the MASTER_PLAN 9.5 figure of 400 ms (PASS, but that row only bounds this setup: 10 patients on SQLite, not 10^5 on PostgreSQL); whole-mix p95 202.55 ms against 200 ms (**FAIL**, by 2.55 ms in this run).
- **Soak** (`SOAK_TEST_HTTP_RESULTS.json`; 1800.49 s, 65,188 requests, concurrency 8, 200 patients): error rate 0.0 % (PASS); RSS growth 11.89 % against 15 % (PASS); overall p95 1001.09 ms (**FAIL**); p95 drift 633.47 ms to 1280.83 ms = 102.19 % against 50 % (**FAIL**). **Latency is not stable over a 30-minute run on this code**: cost still grows with accumulated data.
- Earlier runs are kept: `SOAK_TEST_HTTP_RESULTS_run1_10patients.*` (before the fixes in section 3) and `..._run2_200patients_before_triage_aggregation.*`.
- **Disclosed changes made after seeing results:** the soak patient count went from 10 to 200 (with 10 patients each patient accumulated about 2000 observations, an unrealistic history that the unbounded K2 state turned into the dominant cost; reason recorded in `reports/load/README.md`); a `triage_p95_ms` row from MASTER_PLAN 9.5 was added to the load budgets and the 200 ms whole-mix target was relabelled as the Phase 8b claim rather than a MASTER_PLAN figure (my earlier docstring misattributed it). No budget was loosened.
- **What the 200 ms budget is:** it is the target claimed in Phase 8b, which I carried into the harness before running anything. It is not derived from a requirement.
- Statements about the run in this report refer only to this host, one worker, SQLite, no TLS.

## 5. Web tier (separate PR, stacked)

Branch `fix/web-next15-security`: `next@14.2.35` to `next@15.5.28`, `postcss` override, stale `apps/web/package-lock.json` removed, `npm audit --package-lock-only --omit=dev --audit-level=high` added to CI. Production audit went from 1 critical and 1 high to 0; 26 Playwright tests and the Lighthouse budgets passed on the new version (local run). Dev-tooling advisories remain (build-time; the fix needs `tailwindcss@4`) and are listed in `docs/HANDOVER.md`.

## 6. Repo-standards audit result

`docs/audits/REPO-AUDIT-P15.md` (online mode): T0 3.00 MET, T1 1.83, T2 2.14, T3 2.29, T4 2.17 (**all NOT MET**), T5 2.83 MET; no critical findings. The remaining gaps (single owner, branch protection, signing key, coverage in CI, type checking in CI, metrics endpoint, container image definition, SemVer tag) are listed with their rubric item in that file; those needing the owner are in `docs/HANDOVER.md`.

## 7. Verification run for this tier (local)

`uv run pytest`: 396 passed, 15 skipped (the skips are the env-flag acceptance suites); `uv run ruff check .` clean; `check_claims`, `check_evidence`, `audit_excerpts`, `reality_audit --require-stub-registry`, `verify_hazard_log` (22 cited tests), `verify_study_reproducibility`, `check_docs_links` all pass; acceptance suites with their flags: k1 17, 3b 13, p4 33, p5 6, p7 6, p8 2, p9 2, p11 1, p12 3, p13 1, p14 1 passed. `git diff origin/main --name-only -- 'tests/acceptance_*'` is empty. CI results are reported on the PR.

## 8. Not done in this tier

- `ruff format --check`, a type-check job and coverage measurement in CI (audit items T2.1, T2.5): not added yet; formatting the repository would also touch overseer-owned acceptance tests unless excluded, which needs a decision on scope.
- Signing with the owner's key; GitHub settings; the SemVer tag (owner actions).
- The release manifest is regenerated only at the release candidate (Tier 3).
