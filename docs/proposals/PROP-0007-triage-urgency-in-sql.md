---
id: PROP-0007
title: Triage queue must select its top rows in SQL to meet the 100,000-patient budget
author: Overseer (found while reviewing P16 PR1)
date: 2026-10-19
status: OPEN (next engineering item; supersedes the triage part of PROP-0003)
plan_version_impact: NONE (closes a MASTER_PLAN 9.5 budget gap)
---

# PROP-0007: compute triage urgency and top-N in SQL

## Evidence (script-written: `reports/perf/SCALE_SCALING.json`, runs in `reports/perf/scale_runs/`)
Postgres 15, seeded with one consent, baseline, lab, inference, risk assessment and observations per patient (10% with an overdue task). Triage p95: 2,000 patients 117 ms; 10,000 patients 339 ms; 30,000 patients 1,283 ms. Slope about 0.043 ms per patient, so about 4.3 s at the plan's 100,000 patients against a 400 ms budget. Timeline p95 is 11-13 ms (budget 600 ms): fine.

## What was tried (this PR)
Paging (`limit`/`offset`, `X-Total-Count`) removes serialisation of the whole roster; reading plain columns instead of ORM entities removed about 3 entity constructions per patient (464 to 339 ms at 10,000 patients on the lighter probe). Both are kept. Cost is still linear because every request reads and scores every patient in Python.

## Proposal
Compute the four urgency components in SQL (risk, uncertainty/abstention, overdue follow-up, surveillance delay) from the latest-per-patient rows and order/limit in the database, or maintain a per-patient `triage_state` row updated on writes and recompute only the time-dependent terms (overdue days, days since lab) in the query. Keep `tests/test_triage_batched.py` as the oracle: the SQL result must equal the Python result row for row (including the 4-decimal rounding and tie-breaking) on SQLite and Postgres. Re-run `scripts/run_scale_test_postgres.py` at 2k/10k/30k and 100k (nightly) and require `SCALE_SCALING.json` to say MET.

## Until then
State the supported size honestly: within the 400 ms budget up to about the `patients_within_budget_linear_estimate` in `SCALE_SCALING.json` (about 10,000 patients on the test machine, from the linear fit). A single hospital cohort is well inside that; a regional deployment is not.
