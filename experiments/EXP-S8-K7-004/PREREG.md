# Preregistration: EXP-S8-K7-004 — Patient-grouped cross-fitted causal estimator

**Status:** Registered before implementation and before access to its reserved evaluation seeds  
**Registration date:** 2026-10-20  
**Supersedes:** K7-003's invalid cross-fitting design only; K7-003 artifacts remain preserved and nonconforming  
**Scope:** Synthetic estimator recovery only; no clinical or real-patient inference.

## Objective and estimands

Repeat the K7 synthetic estimator-recovery study with leakage-safe patient-level cross-fitting and collision-free RNG purposes. The primary estimand for each generated cohort remains the finite-cohort marginal risk ratio `mean(P(Y(1)=1 | X,U)) / mean(P(Y(0)=1 | X,U))`; risk difference is secondary. Condition A has measured confounding only. Condition B includes generated `U`, excluded from fitted covariates. Treatment remains delayed radiotherapy, exactly `delay_days > 56`; no ATT, clinical, or real-world causal claim is made.

## Data-generating process

Use the exact K7-003 generator contract and values, without tuning: 5,000 independent synthetic patients per condition and seed; subtype probabilities `(0.35, 0.40, 0.25)`; age `Normal(52,10)` clipped `[25,80]`; stage probabilities `(0.30,0.45,0.25)` for I–III; distance `5 + Exponential(35)` km; breakdown count `Poisson(0.4)`; and `U=0` for A or `Bernoulli(0.30)` for B. Treatment logit is `-1.2 + .5 I(PMRT) + .7 I(TNBC) + .015(D-40) + .4B + .02(age-50) + 1.2U`, with probability `.15 + .70 expit(z)`. Outcome logits are `logit(p0)=-2.5+.4I(PMRT)+.9I(TNBC)+.35(stage-1)+.01(age-50)+1.1U` and `logit(p1)=logit(p0)+log(1.18)`. Potential outcomes are independent conditional on `(X,U)`; observed outcome selects `Y(A)`. Delay days are sampled conditionally such that `A == (delay_days > 56)` for every patient. Truth is calculated from finite-cohort potential-outcome probabilities, never chosen to make an estimator pass. Preserve and report every invalid or non-estimable replicate.

## Estimators and leakage-safe folds

- Primary estimator: AIPW with five-fold stratified cross-fitting. Secondary: cross-fitted g-computation, stabilized IPTW, and unadjusted risk/risk difference. Nuisance learners remain fold-local `StandardScaler` + logistic regression (`lbfgs`, `C=1.0`, `max_iter=1000`). There is no tuning or model selection.
- Every source patient has an immutable integer identity. Point-estimate folds use `StratifiedGroupKFold(n_splits=5, shuffle=True)` with source-patient IDs as groups. For bootstrap replicate `b`, sample source-patient indices with replacement, retain each draw's original source-patient identity as its group, and use grouped stratification. All copies of a source patient must occur in one fold; a property test must fail if any group spans train/held-out partitions. Each patient contributes all sampled copies to exactly one held-out fold. Training and prediction remain over the sampled rows.
- All fold-training arm/outcome-class requirements, propensity bounds `[0.15,0.85]`, weight limit 10, SMD rules, non-estimability rules, and 1,000-resample percentile intervals remain as registered in K7-003. Any interval with more than 5% non-estimable resamples is unavailable. E-values use the original point RR and interval bound nearest null; they describe sensitivity and do not detect hidden confounding.
- The implementation must emit/test exact fold membership or an equivalent audit digest sufficient to verify group disjointness for every bootstrap fit. No resampling is silently discarded.

## Replicates, seeds, and analysis

- Conditions: measured confounding (A) and unmeasured confounding (B), paired on baseline streams.
- Fresh evaluation cohort seeds: `620261141` through `620261160` inclusive. The full range is reserved only for K7-004 and disjoint from K7-001 through K7-003; the runner must verify this reservation and exact range before execution.
- Generator streams use `SeedSequence(s).spawn(6)` in fixed order `(baseline, U, treatment, Y0, Y1, delay)`, as in K7-003.
- RNG purpose codes are fixed and disjoint: point-fold seed `1,000,000,000 + 3,000*i + 1,500*c`; bootstrap-resampling seed `2,000,000,000 + 2*i + c`; bootstrap-fold seed `3,000,000,000 + 3,000*i + 1,500*c + b + 1`, where `i = cohort_seed - 620261141` in `[0,19]`, `c=0` for A and `c=1` for B, and `b` is zero-based in `[0,999]`. Before any cohort is generated, a runner guard and test must enumerate every assigned seed, assert integer bounds accepted by NumPy/scikit-learn, uniqueness within each namespace, and pairwise disjointness across the three namespaces and registered cohort seeds. Seeds are deterministic and may not be changed after data access.
- Preserve all 40 cohort-condition replicates. Report mean, SD, median, range, estimable count, interval coverage denominator, all non-estimability reasons, weight/balance diagnostics, and undefined estimates. H1 uses K7-003's fixed criterion: in A, at least 18/20 cohort-specific 95% intervals cover finite-cohort truth and absolute mean point-estimate error is at most 0.02. Failure is reported without tuning. H2 balance is descriptive. H3 reports B bias/coverage and E-values without an expected-value threshold or detection claim.

## Provenance and execution

1. This registration is committed before implementation and before reading/generating any K7-004 reserved-seed cohort.
2. Implementation and property tests are committed separately. The pre-run access log, including hashes of registration, implementation, runner, verifier, configuration, dependency lock and implementation/registration commits, is committed before the run.
3. A one-time runner refuses dirty trees, duplicate/missing access records, seed-range mismatch, collisions, incorrect ancestry, or any existing output. It writes atomically and never overwrites. The completion manifest binds all source, result, report and runtime hashes.
4. A clean-checkout verifier checks hashes, seed/condition completeness, report parity, and grouped-fold audit evidence without generating cohorts. A separate saved-result arithmetic audit cannot change the preregistered verdict.
5. The historical K7-003 outputs remain preserved with a NONCONFORMING disposition and are not pooled, compared as valid recovery evidence, or replayed.

## Stopping and deviations

No deviations after seed access. If grouped folds cannot be formed, the replicate is retained as non-estimable under a fixed reason code; no alternate split or replacement seed is allowed. Any substantive design change requires another registration on unused seeds. This study cannot establish exchangeability, positivity, transportability, treatment effectiveness, or treatment recommendations in real populations.
