# Sample size: precision criterion (SYNTHETIC ASSUMPTIONS, no partner data)

> Written by `scripts/sample_size_precision.py`. Do not edit by hand. These are arithmetic consequences of assumed sensitivities, interval half-widths and outcome prevalences; no value here is an estimate from real data.

Events needed so that the 95 % Wilson interval for a sensitivity of `p` has half-width at most `d`:

| assumed sensitivity | d = 0.05 | d = 0.10 | d = 0.15 |
|---|---:|---:|---:|
| 0.70 | 320 | 78 | 33 |
| 0.80 | 245 | 60 | 26 |
| 0.90 | 141 | 37 | 17 |

Patients needed for `E` events at a given 365-day outcome prevalence (patients = events / prevalence; ignores loss to follow-up, so a lower bound):

| events | prevalence 0.05 | prevalence 0.10 | prevalence 0.20 |
|---|---:|---:|---:|
| 60 (sens 0.80, d 0.10) | 1200 | 600 | 300 |
| 245 (sens 0.80, d 0.05) | 4900 | 2450 | 1225 |
| 141 (sens 0.90, d 0.05) | 2820 | 1410 | 705 |

PR-05 (minimum events for a subgroup estimate) in `PREREGISTRATION.md` is proposed as 20; with an assumed sensitivity of 0.80 that gives a Wilson half-width of 0.168, which is why a subgroup below it is reported as insufficient.

Not computed (blocked on partner inputs, see `docs/HANDOVER.md`): Riley et al. criteria for prediction-model development; competing-risk and censoring inflation of the required patient count.
