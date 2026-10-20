# Preregistration: EXP-S8-K7-002 — Cross-Fitted Causal Estimator Recovery

**Status:** Registered before implementation and synthetic cohort generation  
**Registration date:** 2026-10-20  
**Supersedes:** none; EXP-S8-K7-001 remains retired under ADR-0068  
**Scope:** Synthetic estimator recovery only. No clinical or real-patient inference.

## 1. Objective and estimands

Evaluate whether cross-fitted IPTW, outcome regression, and AIPW recover the known marginal potential-outcome risk ratio and risk difference under measured confounding, and characterize—not detect—bias under a separately generated unmeasured-confounder condition. Treatment is delayed radiotherapy, defined exactly as initiation more than 56 days after surgery. For each generated cohort, the primary estimand is the finite-cohort marginal risk ratio
`mean(P(Y(1)=1 | X,U)) / mean(P(Y(0)=1 | X,U))`; the risk difference is secondary. `U` is absent in the measured-confounding condition and excluded from fitted covariates in the unmeasured-confounding condition. No ATT estimand is claimed.

## 2. Data-generating process

The new generator is specific to this experiment; it does not reuse or modify the retired generator.

- Generate 5,000 independent synthetic patients per condition and seed.
- Use six measured baseline variables: two subtype indicators, age, stage, travel distance, and equipment-breakdown count. Generate their distributions with the explicit equations and parameters committed in `run.py` before the one-time run.
- In condition A, assign treatment from a logistic model of all six measured covariates. In condition B, add `U ~ Bernoulli(0.30)` to treatment assignment and to the outcome model, while withholding it from estimator inputs. The generator records the true probabilities and finite-cohort potential-outcome risks for audit only; estimator inputs must not contain these values or U.
- Generate treatment `A` once. Generate delay days conditionally so `A == (delay_days > 56)` for every patient: timely days are sampled from integers 14–56 inclusive; delayed days from integers 57–180 inclusive. Assert this invariant before returning the cohort.
- Generate potential outcomes independently conditional on baseline covariates and U from the registered logistic outcome model, then select observed `Y = A*Y(1) + (1-A)*Y(0)`. The conditional treatment coefficient is reported as an odds ratio, never named an RR. The finite-cohort marginal RR/RD are derived from the two potential-outcome probabilities, not chosen to make fitted estimates pass.
- No parameters, seeds, or thresholds may be altered after inspecting any evaluation-seed result. An invalid generated replicate is retained with an explicit failure and cannot be silently replaced.

## 3. Estimators and diagnostics

- Primary estimator: AIPW with patient-level 5-fold stratified cross-fitting. Fold assignment is deterministic from each cohort seed using a separate derived seed. For every held-out fold, fit propensity and both outcome nuisance models only on the other four folds, then predict the held-out rows. No held-out outcomes enter nuisance fitting.
- Secondary estimators: cross-fitted g-computation, stabilized IPTW, and unadjusted risk ratio/risk difference. Report both marginal risks as well as contrasts.
- Propensity estimates are bounded to `[0.01, 0.99]` only after recording the raw minimum/maximum and the number outside the interval. Any cohort with either arm absent, any fold training set lacking either arm/outcome class, non-finite estimates, or a maximum stabilized weight above 10 is declared non-estimable; no winsorization, percentile truncation, arm synthesis, or numeric substitute is permitted.
- Report unweighted and weighted absolute SMDs for all six measured covariates. A zero pooled variance is handled by the exact definition: zero difference gives SMD 0; nonzero difference with zero denominator is undefined and makes the balance summary undefined. No arbitrary variance floor.
- Bootstrap uncertainty: 1,000 patient-level resamples per cohort and condition, percentile 95% intervals, with bootstrap RNG derived from the preregistered seed mapping. Refit cross-fitted nuisances in every resample. Resamples that are structurally non-estimable are counted and reported; if more than 5% are non-estimable, that cohort's interval is unavailable, not computed from a reduced hidden subset.
- Compute E-values only for defined positive AIPW risk ratios. The point E-value uses the original cohort point estimate, and the interval E-value uses the confidence limit nearest the null. E-values are sensitivity summaries, not tests for confounding.

## 4. Replicates, seeds, and analysis

- Conditions: A (measured confounding only) and B (same mechanism plus unmeasured `U`).
- Evaluation cohort seeds: `620261101` through `620261120` inclusive, same seed paired across conditions. These are disjoint from the retired S8-K7-001 seeds `20261017` and `20261018` and are reserved exclusively for this experiment.
- Bootstrap and fold seeds are derived deterministically from the cohort seed and fixed domain-separation constants committed with the implementation. No seed is reused across distinct stochastic purposes.
- Preserve every replicate, including non-estimable replicates. Summaries across seeds include the mean, standard deviation, median, range, count estimable, and fraction of cohort-specific 95% intervals covering that cohort's finite-cohort truth.
- H1 (recovery): in condition A, report AIPW recovery and coverage across all 20 seeds. The criterion is at least 18/20 cohort-specific intervals cover finite-cohort truth and absolute mean point-estimate error across seeds is at most 0.02. A failure is a negative result; do not tune on these seeds.
- H2 (balance): report per-seed maximum weighted SMD and proportion below 0.10; this is descriptive, not a cohort exclusion rule.
- H3 (unmeasured confounding): report condition B bias and interval coverage against the finite-cohort truth, alongside AIPW E-values. The preregistered expected direction is positive bias; no minimum E-value is interpreted as detecting U.
- All confidence summaries, exclusions, and denominators are reported. Missing or undefined estimates remain null with reason codes.

## 5. Execution and provenance

1. Commit this registration before implementing the generator/runner and before accessing the reserved seeds.
2. Commit implementation and its unit/property tests separately; record that implementation commit in an append-only access log before the one-time run.
3. The runner refuses to execute if a completion manifest exists, verifies the registered seed set and source commit, and writes results atomically to this experiment directory only.
4. The completion manifest records registration, implementation, runner, input-contract, output, and report SHA-256 values; runtime versions; seeds; run timestamp; and access-log entry. A clean-checkout verification validates hashes and report/result parity without regenerating cohorts.
5. Historical S8-K7-001 reports remain untouched. This experiment cannot establish real-world exchangeability, positivity, transportability, clinical effectiveness, or treatment recommendations.

## 6. Deviations and stopping

No deviations are permitted after the reserved evaluation seeds are accessed. If the registered design cannot be implemented or a structural validity condition fails, preserve the failure and stop this experiment. Any substantive change requires a new registration and disjoint seed range.
