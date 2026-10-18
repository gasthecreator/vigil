# ADR 0019: M7 ships the explainable urgency ranking; CP-SAT stays a badged research module

## Status
Accepted (implements overseer decision P15-A, `docs/progress/VERDICT-P8B.md`). Supersedes the parts of ADR-0014 and ADR-0015 that describe CP-SAT as the scheduler that the API and UI present by default.

## Context
Study M7-TWIN (`docs/studies/PREREG-M7-TWIN.md`, results in `reports/ml/STUDY_M7_DIGITAL_TWIN.json`, written by `scripts/run_study_m7_twin.py`) compared four policies on a simulated 2-machine department, 12 cells (arrival rate λ ∈ {2.0, 2.5, 3.0, 3.5} × MTTR ∈ {3, 7, 14} days), 50 replications per cell, evaluation seeds `20261017 + rep·100`.

What the committed JSON shows (all synthetic; no real data was used):

- Mean realised harm of the CP-SAT arm is **2.1× to 20.8×** that of the urgency heuristic and **1.9× to 15.1×** that of FCFS across the 12 cells (ratios computed from `sweep_grid[*].mean_harm`).
- CP-SAT gets worse relative to the baselines as arrival rate grows.
- At the baseline cell (λ=2.5, MTTR=7) the paired bootstrap 95% CI of (urgency − CP-SAT) mean harm is [−0.07127, −0.05022]; H1 (beat FCFS) is `REFUTED`; H2 verdict is `URGENCY_ACHIEVES_LOWER_RAW_HARM`.
- The greedy "marginal-harm proxy" arm had a lower mean harm than the urgency heuristic in all 12 cells (point estimates; no CI was pre-registered for this pair). It is a proxy baseline, not a shipped policy, and is recorded here only so that nobody reads the urgency ranking as the best arm tested.

## Decision
1. **The M7 recommendation shipped to API and UI is the explainable urgency ranking** (`RadiotherapyScheduler.rank_urgency`): courses already in progress first; then waiting courses the treating clinician flagged `emergency`/`urgent`; then clinical tier (palliative > curative TNBC > post-mastectomy > post-lumpectomy); then longer elapsed delay. Every assignment carries its priority rank and a reason string.
2. **One addition to the ordering used in the study:** the clinician-flag promotion (step 2) applies only among waiting courses and is not part of the study arm `solve_urgency_heuristic`, whose behaviour is frozen. A test (`test_rank_urgency_equals_frozen_study_arm_without_flags`) asserts that without flags the two produce identical allocations. The flag promotion is therefore **not covered by the simulation evidence**; it implements MASTER_PLAN §6.7 "physician-set hard priorities". The response lists a warning whenever a flagged course is not started within its bound.
3. The ranking enforces **no fairness bound and no starvation ceiling**. The response says so (`fairness_bound_enforced=false`), reports the realised subgroup disparity, and warns when a course has waited past the advisory ceiling.
4. **CP-SAT (`method="cpsat_research"`) is optional and badged.** It is available only to administrators, or when the operator sets `VIGIL_ENABLE_RESEARCH_SCHEDULER=1`; other roles receive HTTP 403. Its responses carry `validation_status="unvalidated in simulation"`. It is promoted only if, on frozen evaluation seeds with bootstrap CIs, it beats both the urgency ranking and FCFS in **every** pre-registered cell (verdict P8B). Research attempts are governed by `docs/studies/PREREG-M7-CPSAT-V2.md`.
5. The ranking itself is labelled `explainable ranking rule; compared only in simulation (synthetic); no real-data validation; requires clinician review`. It is not described as optimal, validated or safe.
6. `is_fairness_certified` is no longer a constant `True`: greedy policies never certify; CP-SAT certifies only when a bound was imposed and the realised disparity respects it.

## Consequences
- Nothing in the product implies that an optimiser protects patients better than a simple rule; the simulation says the opposite for the version evaluated.
- Hazard H10 (RT optimiser inequity/error) and H16 (over-trust in evidence-limited harm model) remain OPEN: the default path now has no fairness constraint, which is traded for explainability and for not being worse than FCFS in simulation.
- The clinician must still confirm every change (`/schedule/confirm`), unchanged.

## What would change this decision
A research formulation that satisfies the promotion criterion above on frozen seeds, or real partner data showing a different picture (`docs/clinical/PREREGISTRATION.md`).
