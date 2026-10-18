# EXP-M7-001 conclusion (SYNTHETIC): not promoted

**Decision.** The research CP-SAT formulation is **not promoted**. The M7 module continues to ship the explainable urgency ranking (ADR-0019). The research code stays in the repository (`packages/vigil-ml/vigil_ml/scheduler_research.py`), is not wired to any API route, and carries no clinical claim.

## What the pre-registered criterion said, and what it showed
- Section 5 criterion (headline harm = wait + interruption, paired bootstrap, 12 cells × 2 baselines): **computed as MET**, 24/24 intervals with lower bound > 0 (`results.json`, `REPORT.md`, written by `scripts/run_study_m7_cpsat_v2.py --mode frozen`, commit `f7e7d0a`). This is reported as computed; it was not edited.
- That criterion was not sufficient: the headline excludes `unscheduled_harm`. The all-in re-evaluation fixed in Amendment 2 (committed before it was run) shows the opposite picture (`ALLIN_ANALYSIS.md`, written by `scripts/analyze_m7_cpsat_v2_allin.py`): research beats urgency and FCFS all-in in **0/12** cells, is significantly worse all-in than at least one baseline in **10/12**, has a significantly longer mean wait in **12/12** (about 25–27 days against 7–20 for urgency) and significantly worse disparity in **11/12** cells. The strongest baseline on the all-in measure is the **urgency ranking in every cell** (proxy second, FCFS last).
- Section 5 makes the criterion necessary ("only if") and requires a fairness/stability re-evaluation before promotion; that re-evaluation failed.

## Diagnosis checklist (PREREG section 7 / MASTER_PLAN §13.3)
| Item | Finding |
|---|---|
| Leakage | The simulator gave the scheduler exact future machine failures. Found on development seeds before any frozen run (Amendment 1), fixed (`downtime_visibility="persistence"`); committed M7-TWIN CP-SAT numbers are therefore optimistic for CP-SAT. No label leakage is possible (no labels). |
| Label noise | Not applicable. |
| Train/test mismatch | **Yes, and it is the finding.** The solver objective (harm-model units, wait + skipped-day interruption) and the realised headline correlate between 0.14 and 0.66 depending on the cell (`REPORT.md`); more importantly neither contains the harm of treatment never delivered, which H-ii removed from the objective by design and the headline never counted. |
| Insufficient signal in the simulator | Not the cause: the gap in mean wait is present in the least loaded cell too (λ = 2.0, MTTR = 3: 24.6 d research vs 7.1 d urgency), so it is not a scarcity effect. |
| Bug | The hard-continuity invariant (no in-progress course skipped while capacity is available) is covered by `packages/vigil-ml/tests/test_scheduler_research.py::test_hard_continuity_never_skips_in_progress_course_when_capacity_is_available`, the objective by `test_objective_matches_independent_recomputation_and_warm_start_bound`, optimality by `test_solver_optimum_equals_brute_force_on_tiny_instances`. These pass; I did not find a bug in the solver. |
| Under-search | A1 (7 d) → A2 (14 d) → A3 (30 d): the headline fell with window length on development seeds (0.0092, 0.0085, 0.0044) as the solver could see further, but that is movement on the incomplete headline, not evidence of better care. |
| Horizon myopia | Same as above: the longest window looked best on the incomplete metric. |
| Mechanism | **Hypothesis, not tested here:** with wait costs tiny relative to the interruption penalty and no value on delivered fractions, the solver prefers to start and finish few courses without interruption and leave the rest waiting. Capacity utilisation and per-course delivery were not recorded in `results.json`, so this is not verified. |

## What would change the decision
A pre-registration whose primary endpoint is all-in harm with mean wait and disparity as co-primary safety endpoints (PROP-0001), a formulation that values completing treatment, and real clinic data on how courses are actually started and delayed.

## Disclosures
- The frozen seeds (`20261017 + 100 r`) were also used for the earlier v1 CP-SAT evaluation; the research formulation was developed on the development seeds only.
- The decision rule of Amendment 2 was written after the frozen run, after the decomposition table had been seen. It is therefore post-hoc; it is reported as such and does not replace the section 5 verdict, which is stated as computed.
- All numbers are from the synthetic M7-TWIN simulator. Nothing here is evidence about real patients or clinical benefit.
