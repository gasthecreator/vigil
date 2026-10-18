# EXP-M7-001 — CP-SAT research track (P15-B): three hypotheses, one promotion criterion

**Status:** PRE-REGISTERED. This file is committed **alone**, before any code for the research scheduler exists and before any run of it. Everything below is fixed at that commit; any later change is an *amendment* appended at the end with its reason and the `git diff`.

**Authority:** `docs/progress/VERDICT-P8B.md` (P15-B), `docs/MASTER_PLAN.md` §13 (elimination protocol), ADR-0019.
**Data:** synthetic only (the M7-TWIN department simulator, `scripts/run_study_m7_twin.py::generate_replication_stream`). Nothing here is evidence about real patients.

## 1. Why this exists
Three earlier rounds changed CP-SAT objective coefficients (P12, P13, P14) without changing the result: in `reports/ml/STUDY_M7_DIGITAL_TWIN.json` CP-SAT mean harm is 2.1×–20.8× the urgency heuristic and 1.9×–15.1× FCFS across the 12 cells (ratios computed from `sweep_grid[*].mean_harm`). This track replaces coefficient hunting by three structural hypotheses. A pre-registered failure is an acceptable outcome (REALITY_RULES RR10).

## 2. Hypotheses (the design is the hypothesis)
- **H-i (hard continuity).** A course already in progress is treated every day on which any capacity is available to in-progress courses. Formally, in each window an in-progress course `c` may be skipped on day `d` (while it still has fractions remaining in the window) **only if** the day's total capacity is entirely used by other in-progress courses. This is a hard constraint, not a penalty.
- **H-ii (harm-only objective).** The objective contains only terms in harm-model units: (a) for every not-yet-started course and every day of the window it has not started, `ContinuityHarmModel.marginal_harm(context, elapsed_delay + d, 1)`; (b) for every skipped day of an in-progress course, `interruption_daily_penalty` of its context (conservative: the 2-day grace of `compute_harm` is not modelled). **No** delivered-fraction reward, **no** continuation reward, **no** switching penalty, **no** idle penalty, **no** day-decay term. Hard constraints other than H-i are capacity and machine downtime only (no fairness bound and no `W_max` in the research arm: they are separate questions and were not part of the evaluated harm).
- **H-iii (rolling horizon with warm start).** The model is re-solved every simulated day over a window and only day 0 is applied. The solver is warm-started (`AddHint`) with the allocation of the urgency ranking (`RadiotherapyScheduler.solve_urgency_heuristic`) for the same window, so that the search starts from the shipped rule and can only improve the *model* objective.

## 3. Attempts (elimination protocol §13: ≥ 3 distinct, competent attempts)
All three share H-i, H-ii, H-iii. They differ in the angle:
- **A1 — baseline research formulation:** window 7 days (as the study), deterministic solver budget `max_deterministic_time = 0.5`.
- **A2 — more search:** window 14 days, `max_deterministic_time = 2.0`.
- **A3 — different angle (occupancy visible):** window 30 days (long enough to cover whole courses of 5–25 fractions, so the solver sees that starting a long course occupies a slot for its duration — the weighted-shortest-processing-time intuition), `max_deterministic_time = 2.0`.
Solver: OR-Tools CP-SAT, `num_workers = 1`, a 20 s wall-clock safety limit only. `max_deterministic_time` makes results independent of machine speed for a fixed OR-Tools version (pinned in `uv.lock`).

## 4. Development vs evaluation (no tuning on evaluation seeds)
- **Development seeds:** replication `r ∈ {0..19}` uses `np.random.default_rng(1000 + 100·r)`; development cells: (λ=2.5, MTTR=7) and (λ=3.5, MTTR=7). All debugging and the choice among A1/A2/A3 use **only** these.
- **Selection rule (fixed now):** the attempt with the lowest mean harm averaged over the two development cells is the single configuration evaluated on frozen seeds. Ties → the smaller window. Dev results of all three attempts are committed (`experiments/EXP-M7-001/dev_results.json`, written by the script) whether or not they are selected.
- **Frozen evaluation seeds:** `np.random.default_rng(20261017 + 100·r)`, `r ∈ {0..49}`, all 12 cells λ ∈ {2.0, 2.5, 3.0, 3.5} × MTTR ∈ {3, 7, 14} (same as M7-TWIN). These seeds were used for the *earlier* v1 CP-SAT evaluation; the research formulation is new and was developed only on the development seeds above, but this reuse is disclosed. The frozen run is executed **once**; if the code changes after it, the old result stays committed and a new amendment/run is added.
- **Policies on the frozen seeds, same replications (paired):** urgency heuristic (`solve_urgency_heuristic` arm as in M7-TWIN), FCFS, greedy marginal-harm proxy, the selected research attempt. The script recomputes the urgency/FCFS/proxy means per cell and **fails** if they differ from the committed `reports/ml/STUDY_M7_DIGITAL_TWIN.json` by more than 1e-5 (same seeds, deterministic).
- Simulator, candidate-pool rule, 60-day horizon, evaluation cohort (arrivals ≤ day 46) and the realised-harm computation are exactly those of `scripts/run_study_m7_twin.py` (imported, not copied).

## 5. Promotion criterion (verbatim from the overseer verdict, operationalised)
The research scheduler is promoted from "research" to a candidate for replacing the urgency ranking **only if**, in **every one of the 12 cells**, both
- `Δ_urg = mean_r(harm_urgency − harm_research)` and
- `Δ_fcfs = mean_r(harm_fcfs − harm_research)`
have a paired-bootstrap 95% CI (percentile, B = 1000, bootstrap RNG seed 20261017, over replications) whose **lower bound is > 0**. That is 24 intervals; one failing interval means "not promoted". There is no pooled test, no Bonferroni-style averaging across cells and no post-hoc cell exclusion.
Promotion would additionally require a separate ADR and a fairness/stability re-evaluation (the research arm enforces no fairness bound).

## 6. What will be reported regardless of outcome
Per cell: mean harm of all arms, `Δ` with CI, harm decomposition (wait/interruption/unscheduled), solver status counts and fraction of decision steps that fell back to the proxy sort, the greedy proxy comparison (secondary, not part of the promotion rule — it was lower than urgency in all 12 cells in M7-TWIN), and the strongest baseline first. Dev results of all attempts. If not promoted: `experiments/EXP-M7-001/CONCLUSION.md` is the elimination record (what was tried, diagnosis checklist of §13.3, what is shipped instead, what would change the decision).

## 7. Diagnosis checklist to be answered in the conclusion (§13.3)
leakage (none possible: synthetic, no labels); label noise (n/a); train/test mismatch (model objective vs realised harm: report the correlation); insufficient signal in the simulator (do the arms differ at all when capacity is slack?); bug (hard-constraint audit: count of skipped in-progress days when capacity was available — must be 0); under-search (A1 vs A2 vs A3); mis-specification of horizon myopia (A3).

## 8. Invariants checked by tests (committed with the solver, before the frozen run)
1. With H-i active, no in-progress course is skipped on a day where capacity for in-progress courses is available (property test over random instances).
2. The objective contains none of the removed terms (the model-building code is asserted by a test that compares the CP-SAT objective with an independent recomputation from the harm model on small instances).
3. Warm start: the first feasible solution's objective is ≤ the urgency ranking's objective in the same model (tested).

## Amendments

### Amendment 1 (before any frozen-seed run): the simulator hands the scheduler the future
**What was observed (development seeds only, one replication, `scripts` smoke run before the dev sweep):** with attempt A3 (30-day window) the realised mean harm of a replication was exactly 0.0, against 0.00632 for the urgency heuristic on the same replication. An exact zero is treated as a defect to investigate, not a result.
**Diagnosis:** in `scripts/run_study_m7_twin.py::simulate_policy_run`, the `CPSAT` arm builds `MachineConfig.down_days` from `remaining_cap[d + h, m]` for every day of the window, i.e. it receives the **exact future machine failures** (day and duration) within the window. Real breakdowns are not known in advance, and the baseline arms (urgency, FCFS, proxy) only see today's capacity. With a long window the scheduler can complete courses before a failure it could not have anticipated, which removes interruption harm. The committed M7-TWIN CP-SAT arm (7-day window) had the same advantage; its committed numbers are therefore *optimistic* for CP-SAT, not pessimistic.
**Change (before any frozen run):** the sim function gains a keyword `downtime_visibility` (`"oracle"` = existing behaviour and default, so the committed M7-TWIN results are unchanged; `"persistence"` = the scheduler sees **today's** capacity of each machine and assumes it persists for the whole window: a machine that is down today is assumed down for the window, one that is up today is assumed up). Day-0 decisions always use true day-0 capacity. **All research attempts and the frozen run use `"persistence"`.**
**Consequences for the protocol:** (1) the development sweep is run under both visibilities; the `"oracle"` development file is committed as evidence of the leak and is **not** used for selection; (2) the attempt selection rule of section 4 is applied to the `"persistence"` development file only; (3) section 5 (promotion criterion) and everything else are unchanged. Note that the frozen seeds have still not been used for the research arm at the time of this amendment.
