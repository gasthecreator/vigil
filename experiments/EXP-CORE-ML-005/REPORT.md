# EXP-CORE-ML-005: synthetic observation-process calibration

> Synthetic simulator mechanics audit only. This does not establish clinical test accuracy, simulator realism, model performance, or verification-bias correction.

- Source commit: `ce897a1bb7c6606578f1bad8baaba998c1698fda`
- Profile SHA-256: `0d591debdba4c7cedff6692d13e49b35cbb002c099d7aeff49d324d71e9d9c3c`
- Patients: 2000 per generator/replicate; five replicates; 730 days.
- All registered cells are included; proportions and Monte Carlo intervals describe only this configuration.

## Imaging propensity

### G1

| Decile | N | Expected mean | Observed rate | Wilson 95% interval |
|---:|---:|---:|---:|---:|
| 1 | 5601 | 0.0351 | 0.0327 | [0.0283, 0.0377] |
| 2 | 5601 | 0.0389 | 0.0393 | [0.0345, 0.0447] |
| 3 | 5597 | 0.0431 | 0.0445 | [0.0394, 0.0502] |
| 4 | 5597 | 0.0477 | 0.0457 | [0.0406, 0.0515] |
| 5 | 5597 | 0.0530 | 0.0523 | [0.0468, 0.0585] |
| 6 | 5597 | 0.0591 | 0.0572 | [0.0514, 0.0636] |
| 7 | 5597 | 0.0654 | 0.0559 | [0.0502, 0.0623] |
| 8 | 5597 | 0.0725 | 0.0733 | [0.0667, 0.0804] |
| 9 | 5596 | 0.5359 | 0.5356 | [0.5225, 0.5486] |
| 10 | 5596 | 0.9500 | 0.9484 | [0.9422, 0.9539] |

### G2

| Decile | N | Expected mean | Observed rate | Wilson 95% interval |
|---:|---:|---:|---:|---:|
| 1 | 5545 | 0.0350 | 0.0377 | [0.0330, 0.0430] |
| 2 | 5545 | 0.0388 | 0.0377 | [0.0330, 0.0430] |
| 3 | 5544 | 0.0430 | 0.0456 | [0.0404, 0.0515] |
| 4 | 5544 | 0.0475 | 0.0532 | [0.0476, 0.0594] |
| 5 | 5543 | 0.0526 | 0.0502 | [0.0447, 0.0562] |
| 6 | 5542 | 0.0581 | 0.0572 | [0.0514, 0.0636] |
| 7 | 5542 | 0.0645 | 0.0659 | [0.0596, 0.0727] |
| 8 | 5542 | 0.0723 | 0.0695 | [0.0631, 0.0765] |
| 9 | 5541 | 0.6036 | 0.6078 | [0.5949, 0.6206] |
| 10 | 5541 | 0.9500 | 0.9469 | [0.9407, 0.9525] |

### G3

| Decile | N | Expected mean | Observed rate | Wilson 95% interval |
|---:|---:|---:|---:|---:|
| 1 | 5581 | 0.0351 | 0.0401 | [0.0353, 0.0456] |
| 2 | 5580 | 0.0389 | 0.0392 | [0.0345, 0.0447] |
| 3 | 5580 | 0.0430 | 0.0439 | [0.0388, 0.0496] |
| 4 | 5580 | 0.0478 | 0.0423 | [0.0373, 0.0479] |
| 5 | 5579 | 0.0533 | 0.0575 | [0.0517, 0.0640] |
| 6 | 5578 | 0.0594 | 0.0665 | [0.0603, 0.0734] |
| 7 | 5578 | 0.0657 | 0.0690 | [0.0627, 0.0760] |
| 8 | 5578 | 0.0729 | 0.0726 | [0.0661, 0.0797] |
| 9 | 5577 | 0.5518 | 0.5487 | [0.5356, 0.5617] |
| 10 | 5577 | 0.9500 | 0.9428 | [0.9364, 0.9486] |

## Imaging result generation

| Generator | Stratum | N performed | Expected positive probability | Observed positive rate | Wilson 95% interval |
|---|---|---:|---:|---:|---:|
| G1 | visible_recurrence | 7670 | 0.9000 | 0.8994784876140808 | [0.8925, 0.9060] |
| G1 | nonvisible_recurrence | 1343 | 0.0100 | 0.006701414743112435 | [0.0035, 0.0127] |
| G1 | no_recurrence | 1535 | 0.0100 | 0.010423452768729642 | [0.0064, 0.0169] |
| G2 | visible_recurrence | 8441 | 0.9000 | 0.8994195000592347 | [0.8928, 0.9057] |
| G2 | nonvisible_recurrence | 901 | 0.0100 | 0.009988901220865706 | [0.0053, 0.0189] |
| G2 | no_recurrence | 1584 | 0.0100 | 0.010101010101010102 | [0.0062, 0.0163] |
| G3 | visible_recurrence | 8009 | 0.9000 | 0.901985266575103 | [0.8953, 0.9083] |
| G3 | nonvisible_recurrence | 1136 | 0.0100 | 0.014084507042253521 | [0.0087, 0.0228] |
| G3 | no_recurrence | 1579 | 0.0100 | 0.01266624445851805 | [0.0082, 0.0195] |

## Assay missingness

| Generator | Analyte | N | Expected mean missing probability | Observed missing rate |
|---|---|---:|---:|---:|
| G1 | albumin | 55976 | 0.0300 | 0.0285 |
| G1 | alp | 55976 | 0.0300 | 0.0297 |
| G1 | alt | 55976 | 0.0300 | 0.0300 |
| G1 | anc | 55976 | 0.0300 | 0.0301 |
| G1 | ast | 55976 | 0.0300 | 0.0291 |
| G1 | ca_15_3 | 55976 | 0.1926 | 0.1892 |
| G1 | ca_27_29 | 55976 | 0.1926 | 0.1921 |
| G1 | calcium | 55976 | 0.0300 | 0.0304 |
| G1 | cea | 55976 | 0.1926 | 0.1949 |
| G1 | corrected_calcium | 55976 | 0.0300 | 0.0313 |
| G1 | creatinine | 55976 | 0.0300 | 0.0285 |
| G1 | crp | 55976 | 0.0300 | 0.0305 |
| G1 | direct_bilirubin | 55976 | 0.0300 | 0.0292 |
| G1 | egfr | 55976 | 0.0300 | 0.0291 |
| G1 | esr | 55976 | 0.0300 | 0.0303 |
| G1 | ggt | 55976 | 0.0300 | 0.0314 |
| G1 | haemoglobin | 55976 | 0.0300 | 0.0294 |
| G1 | inr | 55976 | 0.0300 | 0.0299 |
| G1 | ldh | 55976 | 0.0300 | 0.0298 |
| G1 | nlr | 55976 | 0.0300 | 0.0307 |
| G1 | phosphate | 55976 | 0.0300 | 0.0316 |
| G1 | platelets | 55976 | 0.0300 | 0.0306 |
| G1 | total_bilirubin | 55976 | 0.0300 | 0.0309 |
| G1 | total_protein | 55976 | 0.0300 | 0.0302 |
| G1 | urea | 55976 | 0.0300 | 0.0295 |
| G1 | wbc | 55976 | 0.0300 | 0.0283 |
| G2 | albumin | 55429 | 0.0500 | 0.0503 |
| G2 | alp | 55429 | 0.0500 | 0.0485 |
| G2 | alt | 55429 | 0.0500 | 0.0513 |
| G2 | anc | 55429 | 0.0500 | 0.0496 |
| G2 | ast | 55429 | 0.0500 | 0.0510 |
| G2 | ca_15_3 | 55429 | 0.0500 | 0.0511 |
| G2 | ca_27_29 | 55429 | 0.0500 | 0.0492 |
| G2 | calcium | 55429 | 0.0500 | 0.0511 |
| G2 | cea | 55429 | 0.0500 | 0.0499 |
| G2 | corrected_calcium | 55429 | 0.0500 | 0.0482 |
| G2 | creatinine | 55429 | 0.0500 | 0.0496 |
| G2 | crp | 55429 | 0.0500 | 0.0500 |
| G2 | direct_bilirubin | 55429 | 0.0500 | 0.0500 |
| G2 | egfr | 55429 | 0.0500 | 0.0496 |
| G2 | esr | 55429 | 0.0500 | 0.0495 |
| G2 | ggt | 55429 | 0.0500 | 0.0498 |
| G2 | haemoglobin | 55429 | 0.0500 | 0.0491 |
| G2 | inr | 55429 | 0.0500 | 0.0493 |
| G2 | ldh | 55429 | 0.0500 | 0.0493 |
| G2 | nlr | 55429 | 0.0500 | 0.0504 |
| G2 | phosphate | 55429 | 0.0500 | 0.0518 |
| G2 | platelets | 55429 | 0.0500 | 0.0501 |
| G2 | total_bilirubin | 55429 | 0.0500 | 0.0508 |
| G2 | total_protein | 55429 | 0.0500 | 0.0504 |
| G2 | urea | 55429 | 0.0500 | 0.0501 |
| G2 | wbc | 55429 | 0.0500 | 0.0517 |
| G3 | albumin | 55788 | 0.0600 | 0.0587 |
| G3 | alp | 55788 | 0.0600 | 0.0598 |
| G3 | alt | 55788 | 0.0600 | 0.0600 |
| G3 | anc | 55788 | 0.0600 | 0.0613 |
| G3 | ast | 55788 | 0.0600 | 0.0589 |
| G3 | ca_15_3 | 55788 | 0.0600 | 0.0602 |
| G3 | ca_27_29 | 55788 | 0.0600 | 0.0591 |
| G3 | calcium | 55788 | 0.0600 | 0.0598 |
| G3 | cea | 55788 | 0.0600 | 0.0605 |
| G3 | corrected_calcium | 55788 | 0.0600 | 0.0603 |
| G3 | creatinine | 55788 | 0.0600 | 0.0595 |
| G3 | crp | 55788 | 0.0600 | 0.0615 |
| G3 | direct_bilirubin | 55788 | 0.0600 | 0.0596 |
| G3 | egfr | 55788 | 0.0600 | 0.0604 |
| G3 | esr | 55788 | 0.0600 | 0.0624 |
| G3 | ggt | 55788 | 0.0600 | 0.0596 |
| G3 | haemoglobin | 55788 | 0.0600 | 0.0604 |
| G3 | inr | 55788 | 0.0600 | 0.0591 |
| G3 | ldh | 55788 | 0.0600 | 0.0597 |
| G3 | nlr | 55788 | 0.0600 | 0.0613 |
| G3 | phosphate | 55788 | 0.0600 | 0.0606 |
| G3 | platelets | 55788 | 0.0600 | 0.0592 |
| G3 | total_bilirubin | 55788 | 0.0600 | 0.0597 |
| G3 | total_protein | 55788 | 0.0600 | 0.0626 |
| G3 | urea | 55788 | 0.0600 | 0.0585 |
| G3 | wbc | 55788 | 0.0600 | 0.0584 |

## Facility invariants

| Generator | Patients | Facilities across replicates | Within-facility inconsistencies |
|---|---:|---:|---:|
| G1 | 10000 | 30 | 0 |
| G2 | 10000 | 30 | 0 |
| G3 | 10000 | 30 | 0 |

## G1 high-cost assay missingness by out-of-pocket factor quintile

| Analyte | Quintile | N | Expected mean | Observed missing rate | Wilson 95% interval |
|---|---:|---:|---:|---:|---:|
| ca_15_3 | 1 | 15299 | 0.1362 | 0.1329 | [0.1276, 0.1384] |
| ca_15_3 | 2 | 12469 | 0.1688 | 0.1679 | [0.1614, 0.1745] |
| ca_15_3 | 3 | 10649 | 0.2030 | 0.2024 | [0.1948, 0.2101] |
| ca_15_3 | 4 | 9319 | 0.2364 | 0.2299 | [0.2214, 0.2385] |
| ca_15_3 | 5 | 8240 | 0.2704 | 0.2632 | [0.2538, 0.2728] |
| ca_27_29 | 1 | 15299 | 0.1362 | 0.1323 | [0.1270, 0.1378] |
| ca_27_29 | 2 | 12469 | 0.1688 | 0.1730 | [0.1665, 0.1797] |
| ca_27_29 | 3 | 10649 | 0.2030 | 0.2030 | [0.1955, 0.2108] |
| ca_27_29 | 4 | 9319 | 0.2364 | 0.2319 | [0.2234, 0.2406] |
| ca_27_29 | 5 | 8240 | 0.2704 | 0.2732 | [0.2637, 0.2829] |
| cea | 1 | 15299 | 0.1362 | 0.1381 | [0.1327, 0.1437] |
| cea | 2 | 12469 | 0.1688 | 0.1715 | [0.1650, 0.1783] |
| cea | 3 | 10649 | 0.2030 | 0.2140 | [0.2063, 0.2219] |
| cea | 4 | 9319 | 0.2364 | 0.2384 | [0.2299, 0.2472] |
| cea | 5 | 8240 | 0.2704 | 0.2615 | [0.2522, 0.2711] |

## Facility effect distribution

Per-generator/analyte mean, sample SD, minimum, and maximum for shared facility offsets and scales are in `results.json`; the table above reports within-facility equality checks.

## Interpretation

Read the generated rates against the preregistered configuration and their denominators. These results only diagnose implementation behavior in the named synthetic profile. No result supports a clinical-performance claim or a correction method for selective verification.
