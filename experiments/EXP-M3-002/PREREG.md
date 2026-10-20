# EXP-M3-002: M3 synthetic-assumption sensitivity audit

## Status and boundary

Protocol 1.0, registered 2026-10-20 after documenting the failed EXP-M3-001 execution and before finalizing or committing this study's runner and before generating any new cohort. The inferential design and eligibility rules are fixed here; any earlier implementation draft is discarded. This is a synthetic robustness audit, not model fitting, clinical calibration, or performance validation. It will not select or promote a parameter configuration. EXP-M3-001's generated cohorts were transient and are not reused. S7, P4 acceptance cohorts, and all frozen results are excluded.

## Question and estimand

How sensitive are M3's component scores and action labels to the fixed assumptions declared in the M3 contract when applied to newly generated, independent synthetic trajectories? The estimands are paired within-case changes from the contract configuration: median and 95th-percentile absolute changes in each non-null component score, action-switch proportion, and output/action distributions, stratified by generator and one-factor perturbation. These are sensitivity measures under the registered simulator, not accuracy measures.

## Cohort, eligibility, and access

- Generate 500 patients from each G1 smooth, G2 shedding, and G3 heavy-tailed generator for new seeds `20261024`, `20261025`, and `20261026` (4,500 unique patients total). Use 730-day follow-up and explicitly supply `packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json` (`balanced_synthetic_core_v4`) to every generator. The factory's implicit legacy-v0 default is prohibited. Hash all simulator Python sources and the profile before cohort creation.
- A model input observation is eligible only when `observed_ca_15_3` is true, the CA 15-3 value and day are finite, and the value is strictly positive. Exclude zero, negative, nonfinite, missing, or unobserved values without imputation, clipping, or substitution; report exclusions by stratum. Each evaluated case must have at least three strictly earlier eligible observations. Same-day ties are not prior observations because M3 requires every history day to precede the current day.
- Preserve original M3 history semantics after applying that eligibility rule. Apply the 3% injected-error process only to eligible current observations, with deterministic child seed streams and the baseline configuration's equally weighted population-draw, tenfold-up, and tenfold-down mechanisms. Reuse exactly the same eligible observations and injected values across all registered configurations. Injection labels and recurrence labels are analysis-only and never enter M3 features.
- Do not read or alter S7, P4 acceptance data, or any prior frozen evaluation cohort. The failed EXP-M3-001 execution's transient cohorts are not available and are not reused.

## Registered configurations

The baseline is the current M3 contract configuration: priors `(p_error=0.03, p_real=0.20)`, real-change ratio support `[1.4, 3.0]`, gross-error population draw `lognormal(log(18), 0.6)` and equal mode weights, decimal shift factor `10`, inter-lab CV `0.10`, and action boundaries `(p_error=0.30, p_real=0.60, p_stable=0.90)`. The illustrative CA-marker CV inputs are fixed at `(CVa=0.05, CVi=0.10)` and are not interpreted as patient or analyzer estimates.

Run one-factor-at-a-time perturbations, retaining all other baseline settings (22 perturbations plus the baseline, 23 configurations total):

| Assumption | Registered values |
|---|---|
| Error prior | 0.01, 0.10 |
| Real-change prior | 0.10, 0.35 |
| Real-change ratio support | [1.2, 2.0], [1.8, 4.0] |
| Population-error median | 12, 24 (log SD remains 0.6) |
| Population-error log SD | 0.3, 0.9 (median remains 18) |
| Inter-lab CV | 0.00, 0.20 |
| Decimal-shift factor | 5, 20 |
| Gross-error mode weights | population-heavy `(0.60, 0.20, 0.20)`, decimal-heavy `(0.20, 0.40, 0.40)` |
| `needs_repeat` error boundary | 0.20, 0.40 |
| `escalate` real-change boundary | 0.50, 0.70 |
| `explained` stable boundary | 0.85, 0.95 |

No combined-factor interaction analysis is registered. These brackets are stress settings around the historical synthetic contract, not evidence-based clinical ranges.

## Analysis and integrity

- Report all configurations and every generator/seed stratum. Include eligible evaluations, excluded observation counts, invalid-output and abstention counts, paired score deltas, action-switch rates, action counts, and descriptive AUROCs where both label classes are present. Do not omit sparse or undefined strata.
- Empirical recurrence/error AUROCs are descriptive simulator-label comparisons only; simulator truth and M3 component definitions differ. Do not compute or claim clinical calibration, clinical utility, or an optimal configuration.
- Assert identical model-input and analysis-label hashes across configurations. No configuration may alter inputs, training, feature construction, or labels.
- Commit the runner and tests before cohort access. The runner must refuse a dirty worktree or existing result/access files, record source/environment hashes, and render the report from saved JSON with byte-parity verification. Preserve all results, including sensitivities that make actions unstable.
- The runner's one-time output is `results.json`, `REPORT.md`, and `ACCESS_LOG.json`. Any execution failure after access begins must be preserved; this study ID must not be rerun. A subsequent attempt requires a new preregistration and unseen seeds.

## Limitations

The study measures sensitivity only under the current synthetic generators, their labels, and the chosen stress brackets. It cannot establish that any assumption is clinically plausible, identify a valid prior or cutoff, remedy M3's near-chance recurrence discrimination, or support patient-facing outputs. M3 remains research-only and non-synthetic serving remains abstained.
