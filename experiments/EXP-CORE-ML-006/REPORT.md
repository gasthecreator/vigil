# EXP-CORE-ML-006: synthetic follow-up boundary and observation-process audit

> Synthetic simulator mechanics audit only. This does not establish clinical test accuracy, simulator realism, model performance, or verification-bias correction.

- Source commit: `55581773f7b88c78b084be0f4707960ece3def65`
- Profile SHA-256: `0d591debdba4c7cedff6692d13e49b35cbb002c099d7aeff49d324d71e9d9c3c`
- Patients: 2000 per generator/replicate; five replicates; 730 days; independent seeds from EXP-CORE-ML-005.
- All registered cells are included; proportions and Monte Carlo intervals describe only this configuration.

## Imaging propensity

### G1

| Decile | N | Expected mean | Observed rate | Wilson 95% interval |
|---:|---:|---:|---:|---:|
| 1 | 5137 | 0.0349 | 0.0383 | [0.0334, 0.0440] |
| 2 | 5136 | 0.0383 | 0.0442 | [0.0389, 0.0502] |
| 3 | 5136 | 0.0420 | 0.0370 | [0.0322, 0.0425] |
| 4 | 5136 | 0.0461 | 0.0491 | [0.0435, 0.0553] |
| 5 | 5135 | 0.0509 | 0.0510 | [0.0453, 0.0574] |
| 6 | 5135 | 0.0561 | 0.0563 | [0.0503, 0.0629] |
| 7 | 5135 | 0.0620 | 0.0615 | [0.0553, 0.0684] |
| 8 | 5134 | 0.0683 | 0.0707 | [0.0640, 0.0780] |
| 9 | 5134 | 0.0756 | 0.0810 | [0.0739, 0.0888] |
| 10 | 5132 | 0.8344 | 0.8307 | [0.8202, 0.8407] |

### G2

| Decile | N | Expected mean | Observed rate | Wilson 95% interval |
|---:|---:|---:|---:|---:|
| 1 | 5118 | 0.0348 | 0.0342 | [0.0296, 0.0395] |
| 2 | 5118 | 0.0380 | 0.0418 | [0.0367, 0.0476] |
| 3 | 5117 | 0.0417 | 0.0436 | [0.0383, 0.0495] |
| 4 | 5116 | 0.0462 | 0.0491 | [0.0435, 0.0553] |
| 5 | 5115 | 0.0511 | 0.0491 | [0.0435, 0.0553] |
| 6 | 5115 | 0.0560 | 0.0573 | [0.0512, 0.0640] |
| 7 | 5115 | 0.0617 | 0.0643 | [0.0579, 0.0714] |
| 8 | 5115 | 0.0679 | 0.0755 | [0.0685, 0.0830] |
| 9 | 5115 | 0.0749 | 0.0665 | [0.0600, 0.0736] |
| 10 | 5114 | 0.7937 | 0.7955 | [0.7842, 0.8063] |

### G3

| Decile | N | Expected mean | Observed rate | Wilson 95% interval |
|---:|---:|---:|---:|---:|
| 1 | 5202 | 0.0350 | 0.0346 | [0.0300, 0.0399] |
| 2 | 5202 | 0.0384 | 0.0365 | [0.0318, 0.0420] |
| 3 | 5200 | 0.0422 | 0.0444 | [0.0392, 0.0504] |
| 4 | 5200 | 0.0465 | 0.0392 | [0.0343, 0.0449] |
| 5 | 5200 | 0.0511 | 0.0498 | [0.0442, 0.0561] |
| 6 | 5199 | 0.0562 | 0.0567 | [0.0508, 0.0634] |
| 7 | 5199 | 0.0620 | 0.0583 | [0.0522, 0.0650] |
| 8 | 5199 | 0.0682 | 0.0610 | [0.0548, 0.0678] |
| 9 | 5199 | 0.0750 | 0.0762 | [0.0693, 0.0837] |
| 10 | 5199 | 0.7624 | 0.7715 | [0.7599, 0.7827] |

## Imaging result generation

| Generator | Stratum | N performed | Expected positive probability | Observed positive rate | Wilson 95% interval |
|---|---|---:|---:|---:|---:|
| G1 | visible_recurrence | 3800 | 0.9000 | 0.9010526315789473 | [0.8912, 0.9101] |
| G1 | nonvisible_recurrence | 1339 | 0.0100 | 0.009708737864077669 | [0.0057, 0.0165] |
| G1 | no_recurrence | 1636 | 0.0100 | 0.006723716381418093 | [0.0038, 0.0120] |
| G2 | visible_recurrence | 4000 | 0.9000 | 0.9005 | [0.8908, 0.9094] |
| G2 | nonvisible_recurrence | 872 | 0.0100 | 0.005733944954128441 | [0.0025, 0.0134] |
| G2 | no_recurrence | 1658 | 0.0100 | 0.009047044632086852 | [0.0055, 0.0149] |
| G3 | visible_recurrence | 3816 | 0.9000 | 0.9009433962264151 | [0.8911, 0.9100] |
| G3 | nonvisible_recurrence | 1029 | 0.0100 | 0.007774538386783284 | [0.0039, 0.0153] |
| G3 | no_recurrence | 1541 | 0.0100 | 0.010382868267358857 | [0.0064, 0.0168] |

## Assay missingness

| Generator | Analyte | N | Expected mean missing probability | Observed missing rate |
|---|---|---:|---:|---:|
| G1 | albumin | 51350 | 0.0300 | 0.0296 |
| G1 | alp | 51350 | 0.0300 | 0.0301 |
| G1 | alt | 51350 | 0.0300 | 0.0300 |
| G1 | anc | 51350 | 0.0300 | 0.0302 |
| G1 | ast | 51350 | 0.0300 | 0.0285 |
| G1 | ca_15_3 | 51350 | 0.1939 | 0.1935 |
| G1 | ca_27_29 | 51350 | 0.1939 | 0.1946 |
| G1 | calcium | 51350 | 0.0300 | 0.0307 |
| G1 | cea | 51350 | 0.1939 | 0.1962 |
| G1 | corrected_calcium | 51350 | 0.0300 | 0.0297 |
| G1 | creatinine | 51350 | 0.0300 | 0.0281 |
| G1 | crp | 51350 | 0.0300 | 0.0289 |
| G1 | direct_bilirubin | 51350 | 0.0300 | 0.0298 |
| G1 | egfr | 51350 | 0.0300 | 0.0286 |
| G1 | esr | 51350 | 0.0300 | 0.0297 |
| G1 | ggt | 51350 | 0.0300 | 0.0287 |
| G1 | haemoglobin | 51350 | 0.0300 | 0.0313 |
| G1 | inr | 51350 | 0.0300 | 0.0307 |
| G1 | ldh | 51350 | 0.0300 | 0.0306 |
| G1 | nlr | 51350 | 0.0300 | 0.0292 |
| G1 | phosphate | 51350 | 0.0300 | 0.0295 |
| G1 | platelets | 51350 | 0.0300 | 0.0310 |
| G1 | total_bilirubin | 51350 | 0.0300 | 0.0307 |
| G1 | total_protein | 51350 | 0.0300 | 0.0307 |
| G1 | urea | 51350 | 0.0300 | 0.0284 |
| G1 | wbc | 51350 | 0.0300 | 0.0317 |
| G2 | albumin | 51158 | 0.0500 | 0.0493 |
| G2 | alp | 51158 | 0.0500 | 0.0485 |
| G2 | alt | 51158 | 0.0500 | 0.0507 |
| G2 | anc | 51158 | 0.0500 | 0.0492 |
| G2 | ast | 51158 | 0.0500 | 0.0528 |
| G2 | ca_15_3 | 51158 | 0.0500 | 0.0505 |
| G2 | ca_27_29 | 51158 | 0.0500 | 0.0513 |
| G2 | calcium | 51158 | 0.0500 | 0.0491 |
| G2 | cea | 51158 | 0.0500 | 0.0489 |
| G2 | corrected_calcium | 51158 | 0.0500 | 0.0479 |
| G2 | creatinine | 51158 | 0.0500 | 0.0500 |
| G2 | crp | 51158 | 0.0500 | 0.0487 |
| G2 | direct_bilirubin | 51158 | 0.0500 | 0.0507 |
| G2 | egfr | 51158 | 0.0500 | 0.0516 |
| G2 | esr | 51158 | 0.0500 | 0.0497 |
| G2 | ggt | 51158 | 0.0500 | 0.0507 |
| G2 | haemoglobin | 51158 | 0.0500 | 0.0493 |
| G2 | inr | 51158 | 0.0500 | 0.0499 |
| G2 | ldh | 51158 | 0.0500 | 0.0486 |
| G2 | nlr | 51158 | 0.0500 | 0.0503 |
| G2 | phosphate | 51158 | 0.0500 | 0.0487 |
| G2 | platelets | 51158 | 0.0500 | 0.0501 |
| G2 | total_bilirubin | 51158 | 0.0500 | 0.0500 |
| G2 | total_protein | 51158 | 0.0500 | 0.0517 |
| G2 | urea | 51158 | 0.0500 | 0.0497 |
| G2 | wbc | 51158 | 0.0500 | 0.0497 |
| G3 | albumin | 51999 | 0.0600 | 0.0627 |
| G3 | alp | 51999 | 0.0600 | 0.0593 |
| G3 | alt | 51999 | 0.0600 | 0.0600 |
| G3 | anc | 51999 | 0.0600 | 0.0607 |
| G3 | ast | 51999 | 0.0600 | 0.0605 |
| G3 | ca_15_3 | 51999 | 0.0600 | 0.0621 |
| G3 | ca_27_29 | 51999 | 0.0600 | 0.0586 |
| G3 | calcium | 51999 | 0.0600 | 0.0592 |
| G3 | cea | 51999 | 0.0600 | 0.0603 |
| G3 | corrected_calcium | 51999 | 0.0600 | 0.0598 |
| G3 | creatinine | 51999 | 0.0600 | 0.0594 |
| G3 | crp | 51999 | 0.0600 | 0.0593 |
| G3 | direct_bilirubin | 51999 | 0.0600 | 0.0583 |
| G3 | egfr | 51999 | 0.0600 | 0.0605 |
| G3 | esr | 51999 | 0.0600 | 0.0608 |
| G3 | ggt | 51999 | 0.0600 | 0.0600 |
| G3 | haemoglobin | 51999 | 0.0600 | 0.0592 |
| G3 | inr | 51999 | 0.0600 | 0.0604 |
| G3 | ldh | 51999 | 0.0600 | 0.0598 |
| G3 | nlr | 51999 | 0.0600 | 0.0579 |
| G3 | phosphate | 51999 | 0.0600 | 0.0611 |
| G3 | platelets | 51999 | 0.0600 | 0.0596 |
| G3 | total_bilirubin | 51999 | 0.0600 | 0.0611 |
| G3 | total_protein | 51999 | 0.0600 | 0.0617 |
| G3 | urea | 51999 | 0.0600 | 0.0600 |
| G3 | wbc | 51999 | 0.0600 | 0.0602 |

## Facility invariants

| Generator | Patients | Facilities across replicates | Within-facility inconsistencies |
|---|---:|---:|---:|
| G1 | 10000 | 30 | 0 |
| G2 | 10000 | 30 | 0 |
| G3 | 10000 | 30 | 0 |

## G1 high-cost assay missingness by out-of-pocket factor quintile

| Analyte | Quintile | N | Expected mean | Observed missing rate | Wilson 95% interval |
|---|---:|---:|---:|---:|---:|
| ca_15_3 | 1 | 13815 | 0.1364 | 0.1341 | [0.1285, 0.1398] |
| ca_15_3 | 2 | 11446 | 0.1700 | 0.1746 | [0.1677, 0.1816] |
| ca_15_3 | 3 | 9790 | 0.2042 | 0.2008 | [0.1930, 0.2089] |
| ca_15_3 | 4 | 8610 | 0.2374 | 0.2419 | [0.2330, 0.2511] |
| ca_15_3 | 5 | 7689 | 0.2709 | 0.2651 | [0.2553, 0.2750] |
| ca_27_29 | 1 | 13815 | 0.1364 | 0.1342 | [0.1286, 0.1400] |
| ca_27_29 | 2 | 11446 | 0.1700 | 0.1789 | [0.1720, 0.1861] |
| ca_27_29 | 3 | 9790 | 0.2042 | 0.2057 | [0.1978, 0.2138] |
| ca_27_29 | 4 | 8610 | 0.2374 | 0.2339 | [0.2251, 0.2430] |
| ca_27_29 | 5 | 7689 | 0.2709 | 0.2684 | [0.2586, 0.2785] |
| cea | 1 | 13815 | 0.1364 | 0.1371 | [0.1315, 0.1429] |
| cea | 2 | 11446 | 0.1700 | 0.1767 | [0.1698, 0.1838] |
| cea | 3 | 9790 | 0.2042 | 0.2040 | [0.1961, 0.2121] |
| cea | 4 | 8610 | 0.2374 | 0.2403 | [0.2314, 0.2494] |
| cea | 5 | 7689 | 0.2709 | 0.2719 | [0.2621, 0.2820] |

## Facility effect distribution

Per-generator/analyte mean, sample SD, minimum, and maximum for shared facility offsets and scales are in `results.json`; the table above reports within-facility equality checks.

## Follow-up boundary checks

| Generator | Patients | Confirmed recurrence | Post-recurrence violations | Competing event | Post-competing violations | No observations | Single day-zero fallback |
|---|---:|---:|---:|---:|---:|---:|---:|
| G1 | 10000 | 2847 | 0 | 883 | 0 | 0 | 0 |
| G2 | 10000 | 2991 | 0 | 888 | 0 | 0 | 0 |
| G3 | 10000 | 2863 | 0 | 878 | 0 | 0 | 0 |

## Interpretation

Read the generated rates against the preregistered configuration and their denominators. These results only diagnose implementation behavior in the named synthetic profile. No result supports a clinical-performance claim or a correction method for selective verification.
