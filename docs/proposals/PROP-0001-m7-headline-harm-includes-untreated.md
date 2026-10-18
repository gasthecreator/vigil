---
id: PROP-0001
title: M7 headline harm must include harm of fractions never delivered
author: Executor (final-build Tier 0)
date: 2026-10-18
status: DRAFT
plan_version_impact: NONE (study definition; docs/studies/PREREG-M7-TWIN.md section 6 and experiments/EXP-M7-001/PREREG.md)
---

# PROP-0001: M7 headline harm must include harm of fractions never delivered

## 1. Problem Statement
In `scripts/run_study_m7_twin.py` the headline per-policy figure `mean_harm` is wait harm + interruption harm. `unscheduled_harm` (harm attributable to fractions never delivered within the horizon) is computed but reported separately (`docs/studies/PREREG-M7-TWIN.md` section 6 defines `total_harm` as wait + interruption). A policy can therefore lower the headline by not delivering treatment. EXP-M7-001 produced exactly that: the research CP-SAT formulation "beat" urgency and FCFS in 12/12 cells on the headline while delivering far less treatment (all-in harm worse in 10/12 cells with CI excluding zero, mean wait 25-27 days vs 7-20; see `experiments/EXP-M7-001/ALLIN_ANALYSIS.md`).

## 2. Evidence Base
`experiments/EXP-M7-001/results.json` (per-replication values), `REPORT.md` (decomposition table), `ALLIN_ANALYSIS.md`, PREREG Amendment 2.

## 3. Proposed Change
Make **all-in harm = wait + interruption + unscheduled** the primary endpoint of any scheduler study, with mean wait (days) and subgroup disparity as co-primary safety endpoints, and keep the current headline as a secondary decomposition. Pre-registrations for scheduler studies state the all-in definition and the rule that a policy that increases mean wait or untreated fractions significantly cannot be promoted regardless of the headline.

## 4. Considered Alternatives
- **Keep the headline, add a warning.** Pros: no change to committed M7-TWIN numbers. Cons: the loophole stays; the next optimiser will find it again.
- **Add a delivered-fraction reward to the optimiser (undoing H-ii).** Pros: removes the incentive. Cons: reintroduces non-harm units, which is the coefficient hunt P15-B was meant to end; it does not fix the metric.

## 5. Evaluation & Verification Criteria
Re-run the M7-TWIN committed arms under the all-in definition (no new simulation needed; `unscheduled_harm` is already in the per-replication data) and report whether the ordering of urgency / FCFS / proxy changes. Test: a unit test that fails if a scheduler study report's headline omits `unscheduled_harm`.

## 6. Kill / Rollback Criterion
If all-in harm is dominated by a term that cannot be tied to the harm model (the unscheduled term depends on the 60-day horizon and on `base_event_rate`), abandon all-in as primary and instead fix the horizon problem (follow patients to completion).

## 7. Impact on Master Plan
None directly; the overseer decides whether the M7-TWIN pre-registration is amended.
