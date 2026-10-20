# EXP-SIM-CAL-E1-001 deviation: evaluator contract failure

**Status:** Aborted after first generated cohort; no results are reportable.

## Event

The frozen runner started from source commit `302edf132040d5c2442ba8bd7ac6e4ab6189be9f` with preregistration commit `245f03e9801ab7ac887a4f1e4072461efecee49c`. It generated the first registered cohort, G1 replicate 0, seed `514100`. Evaluation raised `ValueError: observed diagnosis precedes latent recurrence onset`. The access log records the start, seed, and failure. No result row, `results.json`, report, or completion manifest was written. This attempt is preserved and must not be rerun.

## Root cause

The evaluator incorrectly assumed `true_recurrence_day` must precede the observed diagnosis day. In the v4 G1 generator, burden begins at a configured seeding time computed as `true_recurrence_day - target_lead - seed_offset_days`; the observed verification event can therefore validly precede the simulator's nominal `true_recurrence_day`. That field is not an ordering constraint for the source-aligned observed-diagnosis estimand. The simulator and its profile were not changed.

## Disposition

Do not edit this experiment's preregistration, rerun its seed, or describe it as a completed study. A corrected evaluator contract and any new cohort access require a separately preregistered experiment ID and a fresh, collision-audited seed namespace. The failure cohort was generated in memory but the runner wrote no cohort data or metric row; only the access/failure record remains.

