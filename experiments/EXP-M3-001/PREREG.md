# EXP-M3-001: M3 synthetic-assumption sensitivity audit

## Status and boundary

Protocol 1.0, registered 2026-10-20 before implementation or cohort generation. This is a synthetic robustness audit, not model fitting, clinical calibration, or performance validation. It will not select or promote a parameter configuration. S7, P4 acceptance cohorts, and all frozen results are excluded.

## Question and estimand

How sensitive are M3's component scores and action labels to the fixed assumptions declared in the M3 contract when applied to newly generated, independent synthetic trajectories? The estimands are paired within-patient changes from the contract configuration: median and 95th-percentile absolute changes in each non-null component score, action-switch proportion, and output/action distributions, stratified by generator and one-factor perturbation. These are sensitivity measures under the registered simulator, not accuracy measures.

## Cohort and access

- Generate 500 patients from each of G1 smooth, G2 shedding, and G3 heavy-tailed generators for seeds `20261021`, `20261022`, and `20261023` (4,500 unique patients total). Use 730-day follow-up and the generator's current committed profile. Hash the profile and generator source before cohort creation.
- Evaluate each eligible observed CA 15-3 visit after at least three strictly prior observed visits. Preserve original M3 history semantics. Apply the preregistered 3% injected-error process with equally likely population-draw, tenfold-up, and tenfold-down modes, using separate deterministic child seed streams. Retain patient, visit, generator, seed, lab-switch, and injection indicators for analysis only; none enter M3 features.
- Reuse exactly the same generated records and injected values across the baseline and each parameter perturbation. Do not read or alter S7, acceptance, or any prior frozen evaluation cohort.

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

- Report all 23 configurations, each generator and seed separately; do not omit failed, undefined, or sparse strata.
- For each configuration, report baseline-paired component score deltas, absolute-delta quantiles, action-switch rates, action counts, and invalid/abstention counts. Report empirical recurrence/error AUROC only as descriptive simulator-label comparisons, with an explicit warning that simulator truth and M3's component definitions differ. Do not compute or claim clinical calibration, clinical utility, or an optimal configuration.
- Assert identical cohort and injected-value hashes across configurations; no configuration may change inputs, training, feature construction, or labels.
- Commit the runner and tests before generating the registered cohorts. The runner must refuse a dirty worktree or existing result/access files, write complete JSON and source/environment hashes, and render the report from saved JSON with byte-parity verification. Preserve all results, including sensitivities that make actions unstable.
- The analysis must not mutate M3 defaults, acceptance tests, thresholds, or historical artifacts. Any follow-up tuning or new performance study requires a new preregistration and unseen seeds.

## Amendment before runner implementation or cohort access (2026-10-20)

The factory's implicit default is `legacy_synthetic_population_v0.json`, which is not the current mechanism profile. This registered study instead supplies `packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json` explicitly to all three generators. Its profile identifier is `balanced_synthetic_core_v4`; it includes the audited G1 clearance and G2 shot-noise mechanisms. The runner must record this exact file's hash and must not use the factory's legacy default. No implementation or cohort output was accessed before this amendment.

## Limitations

The study measures sensitivity only under the current synthetic generators, their labels, and the chosen stress brackets. It cannot establish that any assumption is clinically plausible, identify a valid prior or cutoff, remedy M3's near-chance recurrence discrimination, or support patient-facing outputs. M3 remains research-only and non-synthetic serving remains abstained.
