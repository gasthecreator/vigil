# EXP-K5-001 report (written by `run.py`; do not edit)

> **SYNTHETIC DATA ONLY.** Laboratory spreads: tau = 0.07 is anchored by E23 (a spread across laboratories in a Chinese EQA programme, not a bias estimate); tau = 0.15 and 0.30 are assumptions. Rule R (a 25 percent rise) is a study rule, not a clinical criterion. Pre-registration: `PREREG.md`.

Replications: 100 (frozen seeds). Detector calibration: sigma_r = 0.1651, threshold h* = 15.00 from 120 null streams (56048 residuals). **Calibration target of 0.67 alarms per 1,000 residuals attained: False** (achieved 156.76 per 1,000 at h* = 15.00). Run time 905 s.

Diagnostic added by Amendment 2 (alarm rate per 1,000 calibration residuals against threshold; not used to choose anything):

| threshold | all residuals | residuals of patients without recurrence only |
|---|---|---|
| 2 | 304.70 | 0.91 |
| 5 | 264.74 | 0.00 |
| 10 | 206.14 | 0.00 |
| 15 | 156.76 | 0.00 |
| 30 | 88.80 | 0.00 |
| 60 | 47.50 | 0.00 |

## Hypotheses (computed)

| Hypothesis | Result | Detail |
|---|---|---|
| H1 `tau0.07_sw0.10` | NOT met | excess FAR of pooled over oracle = 0.0048 (threshold 0.05) |
| H1 `tau0.07_sw0.30` | NOT met | excess FAR of pooled over oracle = 0.0125 (threshold 0.05) |
| H1 `tau0.15_sw0.10` | NOT met | excess FAR of pooled over oracle = 0.0164 (threshold 0.05) |
| H1 `tau0.15_sw0.30` | NOT met | excess FAR of pooled over oracle = 0.0470 (threshold 0.05) |
| H1 `tau0.30_sw0.10` | NOT met | excess FAR of pooled over oracle = 0.0268 (threshold 0.05) |
| H1 `tau0.30_sw0.30` | met | excess FAR of pooled over oracle = 0.0806 (threshold 0.05) |
| H2 `k3` | met | RMSE(fixed) - RMSE(K5) = 0.3535, Bonferroni interval [0.2972, 0.4140] |
| H2 `k10` | met | RMSE(fixed) - RMSE(K5) = 0.1403, Bonferroni interval [0.1129, 0.1710] |
| H3 | NOT met | recovered fraction 0.520, 95% [0.438, 0.593], Bonferroni lower 0.412; Sens K5 0.834 vs oracle 0.833 |
| H4 `tau0.07_sw0.10` | NOT met | K5 95% interval coverage 0.615 |
| H4 `tau0.07_sw0.30` | NOT met | K5 95% interval coverage 0.719 |
| H4 `tau0.15_sw0.10` | NOT met | K5 95% interval coverage 0.687 |
| H4 `tau0.15_sw0.30` | NOT met | K5 95% interval coverage 0.825 |
| H4 `tau0.30_sw0.10` | NOT met | K5 95% interval coverage 0.817 |
| H4 `tau0.30_sw0.30` | NOT met | K5 95% interval coverage 0.897 |
| H5 | NOT met | power 1.0, median delay 9.586696333191554 days, null alarms per 1000 results 153.836 |

**Kill rule fires:** True (H3 failed: True; K5 beats fixed on E2 with non-overlapping interval: False; H2 met at k=3 or 10: True).

## E1: contrast RMSE (log units, mean over replications; lower is better; oracle is 0 by definition)

| Cell | pooled | legacy | fixed | K5 | tau_hat mean (true tau) | coverage fixed | coverage K5 |
|---|---|---|---|---|---|---|---|
| `tau0.07_sw0.10` | 0.0995 | 0.1355 | 0.2835 | 0.1469 | 0.111 (0.07) | 0.904 | 0.615 |
| `tau0.07_sw0.30` | 0.0995 | 0.1269 | 0.1560 | 0.0996 | 0.083 (0.07) | 0.912 | 0.719 |
| `tau0.15_sw0.10` | 0.2132 | 0.1355 | 0.2835 | 0.2036 | 0.166 (0.15) | 0.904 | 0.687 |
| `tau0.15_sw0.30` | 0.2132 | 0.1270 | 0.1560 | 0.1329 | 0.157 (0.15) | 0.912 | 0.825 |
| `tau0.30_sw0.10` | 0.4264 | 0.1359 | 0.2835 | 0.2520 | 0.310 (0.30) | 0.904 | 0.817 |
| `tau0.30_sw0.30` | 0.4264 | 0.1274 | 0.1560 | 0.1486 | 0.308 (0.30) | 0.912 | 0.897 |
| `tau0.15_sw0.30_casemix` | 0.2132 | 0.1456 | 0.1666 | 0.1408 | 0.155 (0.15) | 0.899 | 0.803 |

## Control (Amendment 2): the K5 model is exactly true (log-linear patient trajectories on the simulator's visit schedule), cell tau 0.15, switching 0.30

| pooled | legacy | fixed | K5 | tau_hat mean (true 0.15) | coverage fixed | coverage K5 |
|---|---|---|---|---|---|---|
| 0.2132 | 0.0624 | 0.0202 | 0.0203 | 0.150 | 0.955 | 0.949 |

## E2: rule R, false alarms (FAR) and sensitivity, mean over replications

| Cell | method | FAR | Sens | recovered fraction (95% CI) |
|---|---|---|---|---|
| `tau0.07_sw0.10` | pooled | 0.0126 | 0.8328 |  |
| `tau0.07_sw0.10` | legacy | 0.0154 | 0.8329 | n/a (excess < 0.01) |
| `tau0.07_sw0.10` | fixed | 0.0269 | 0.8325 | n/a (excess < 0.01) |
| `tau0.07_sw0.10` | k5 | 0.0168 | 0.8328 | n/a (excess < 0.01) |
| `tau0.07_sw0.10` | oracle | 0.0078 | 0.8328 |  |
| `tau0.07_sw0.30` | pooled | 0.0204 | 0.8330 |  |
| `tau0.07_sw0.30` | legacy | 0.0261 | 0.8326 | -0.458 [-0.885, -0.143] |
| `tau0.07_sw0.30` | fixed | 0.0390 | 0.8330 | -1.485 [-2.195, -0.975] |
| `tau0.07_sw0.30` | k5 | 0.0210 | 0.8331 | -0.048 [-0.348, 0.173] |
| `tau0.07_sw0.30` | oracle | 0.0078 | 0.8328 |  |
| `tau0.15_sw0.10` | pooled | 0.0242 | 0.8328 |  |
| `tau0.15_sw0.10` | legacy | 0.0154 | 0.8329 | 0.537 [0.428, 0.632] |
| `tau0.15_sw0.10` | fixed | 0.0269 | 0.8325 | -0.161 [-0.358, 0.020] |
| `tau0.15_sw0.10` | k5 | 0.0221 | 0.8327 | 0.130 [0.014, 0.242] |
| `tau0.15_sw0.10` | oracle | 0.0078 | 0.8328 |  |
| `tau0.15_sw0.30` | pooled | 0.0548 | 0.8336 |  |
| `tau0.15_sw0.30` | legacy | 0.0262 | 0.8326 | 0.609 [0.535, 0.677] |
| `tau0.15_sw0.30` | fixed | 0.0390 | 0.8330 | 0.337 [0.218, 0.443] |
| `tau0.15_sw0.30` | k5 | 0.0304 | 0.8335 | 0.520 [0.438, 0.593] |
| `tau0.15_sw0.30` | oracle | 0.0078 | 0.8328 |  |
| `tau0.30_sw0.10` | pooled | 0.0346 | 0.8320 |  |
| `tau0.30_sw0.10` | legacy | 0.0155 | 0.8330 | 0.714 [0.654, 0.769] |
| `tau0.30_sw0.10` | fixed | 0.0269 | 0.8325 | 0.290 [0.199, 0.379] |
| `tau0.30_sw0.10` | k5 | 0.0259 | 0.8325 | 0.328 [0.254, 0.399] |
| `tau0.30_sw0.10` | oracle | 0.0078 | 0.8328 |  |
| `tau0.30_sw0.30` | pooled | 0.0884 | 0.8324 |  |
| `tau0.30_sw0.30` | legacy | 0.0262 | 0.8326 | 0.772 [0.734, 0.809] |
| `tau0.30_sw0.30` | fixed | 0.0390 | 0.8330 | 0.613 [0.559, 0.667] |
| `tau0.30_sw0.30` | k5 | 0.0355 | 0.8331 | 0.656 [0.608, 0.704] |
| `tau0.30_sw0.30` | oracle | 0.0078 | 0.8328 |  |
| `tau0.15_sw0.30_casemix` | pooled | 0.0555 | 0.8336 |  |
| `tau0.15_sw0.30_casemix` | legacy | 0.0410 | 0.8349 | 0.304 [0.187, 0.407] |
| `tau0.15_sw0.30_casemix` | fixed | 0.0407 | 0.8328 | 0.310 [0.182, 0.424] |
| `tau0.15_sw0.30_casemix` | k5 | 0.0328 | 0.8330 | 0.476 [0.388, 0.556] |
| `tau0.15_sw0.30_casemix` | oracle | 0.0078 | 0.8328 |  |

## New sites (cell tau 0.15, switching 0.30): E1 contrast RMSE new laboratory vs network, and descriptive E2 on switchers to a new laboratory

| k switching patients per new lab | RMSE pooled | RMSE legacy | RMSE fixed | RMSE K5 | fixed - K5 (95% CI) | coverage fixed | coverage K5 | FAR pooled | FAR fixed | FAR K5 | FAR oracle |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.2041 | 0.1726 | 0.1833 | 0.1731 | 0.0102 [0.0065, 0.0135] | n/a | 0.820 | 0.0605 | 0.0568 | 0.0533 | 0.0078 |
| 3 | 0.2041 | 0.3054 | 0.5423 | 0.1887 | 0.3535 [0.3062, 0.4032] | 0.897 | 0.830 | 0.0605 | 0.1018 | 0.0546 | 0.0078 |
| 10 | 0.2041 | 0.3411 | 0.3162 | 0.1758 | 0.1403 [0.1178, 0.1643] | 0.932 | 0.824 | 0.0605 | 0.0842 | 0.0507 | 0.0078 |
| 30 | 0.2041 | 0.3051 | 0.2111 | 0.1559 | 0.0552 [0.0426, 0.0670] | 0.912 | 0.854 | 0.0605 | 0.0638 | 0.0461 | 0.0078 |

## E3: laboratory-stream detector (shifted laboratory 2 from calendar day 365; tau 0.07, switching 0.30)

| delta | null alarms per 1000 results | power (within 180 d) | median delay (days) | IQR delay (days) | median delay (lab results) |
|---|---|---|---|---|---|
| 0.00 | 153.836 | n/a | n/a | n/a | n/a |
| 0.10 | 150.250 | 1.0 | 12.719054628265354 | [6.438680729558385, 23.637192829995058] | 6.0 |
| 0.20 | 150.031 | 1.0 | 9.586696333191554 | [4.989683781834998, 17.811848885530054] | 5.0 |
| 0.30 | 149.645 | 1.0 | 8.794723996715163 | [4.702051316482752, 16.818044813184756] | 4.0 |

## E4 (descriptive): shifted laboratory, delta 0.20, rule R among patients with a post-shift result there

| arm | FAR | Sens | FAR n/d | Sens n/d |
|---|---|---|---|---|
| without_withholding | 0.29650727027432167 | 0.6760961810466761 | 1978/6671 | 4302/6363 |
| with_withholding | 0.014090840953380302 | 0.003928964325003929 | 94/6671 | 25/6363 |

## Limits (carried from the pre-registration)
Synthetic data; proportional laboratory bias only; offsets identified only through patients who change laboratory; no reference-material anchoring; one analyte; a single step change as the only temporal drift; rule R is a study rule.

