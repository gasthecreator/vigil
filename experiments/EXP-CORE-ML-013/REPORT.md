# EXP-CORE-ML-013: v4 simulator call-path mechanism verification

Synthetic mechanism implementation audit only; no calibration, predictive-performance, population, or clinical claim.
Source commit: `87ba7ad8e9094bb1057b65ad77b5ed757f3089fe`

## G1 recurrence counts and G2 event-process diagnostics

| Replicate | G1 true recurrences | G2 true recurrences | G2 eligible recurrences | G2 eligible person-time (days) | G2 events | Poisson p | Event-time KS p | Amplitude KS p |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 465 | 481 | 481 | 236026.565 | 4846 | 0.0688517 | 0.844738 | 0.794296 |
| 1 | 471 | 461 | 461 | 229989.175 | 4517 | 0.223824 | 0.250941 | 0.0886909 |
| 2 | 472 | 470 | 470 | 229337.453 | 4456 | 0.0539861 | 0.593646 | 0.489723 |
| 3 | 466 | 456 | 456 | 221302.470 | 4361 | 0.332286 | 0.974877 | 0.746822 |
| 4 | 467 | 512 | 512 | 253917.114 | 5200 | 0.0881967 | 0.493125 | 0.113593 |

## Holm-adjusted diagnostics

### Replicate 0

- G2 event-count mean/variance per eligible recurrent patient: 10.074844074844075 / 20.977720027720025.
- Amplitude mean/CV: 14.977453243970876 / 0.49662027617995935; standardized lognormal KS statistic: 0.009281981868604738.
- Exclusions: `{"missing_recurrence_day": 0, "not_true_recurrence": 519, "zero_exposure": 0}`.
- Holm-adjusted p-values: `{"amplitude_lognormality": 1.0, "event_time_uniformity": 1.0, "poisson_count": 0.20655518377793322}`; reject at alpha 0.01: `{"amplitude_lognormality": false, "event_time_uniformity": false, "poisson_count": false}`.

### Replicate 1

- G2 event-count mean/variance per eligible recurrent patient: 9.79826464208243 / 20.100518721116668.
- Amplitude mean/CV: 14.865716621665456 / 0.4963810357005573; standardized lognormal KS statistic: 0.01853386776791688.
- Exclusions: `{"missing_recurrence_day": 0, "not_true_recurrence": 539, "zero_exposure": 0}`.
- Holm-adjusted p-values: `{"amplitude_lognormality": 0.2660725865397472, "event_time_uniformity": 0.4476476220446764, "poisson_count": 0.4476476220446764}`; reject at alpha 0.01: `{"amplitude_lognormality": false, "event_time_uniformity": false, "poisson_count": false}`.

### Replicate 2

- G2 event-count mean/variance per eligible recurrent patient: 9.480851063829787 / 19.88769223789865.
- Amplitude mean/CV: 14.956577548635417 / 0.48838608052222987; standardized lognormal KS statistic: 0.012458646687945496.
- Exclusions: `{"missing_recurrence_day": 0, "not_true_recurrence": 530, "zero_exposure": 0}`.
- Holm-adjusted p-values: `{"amplitude_lognormality": 0.9794461967161243, "event_time_uniformity": 0.9794461967161243, "poisson_count": 0.16195837352927858}`; reject at alpha 0.01: `{"amplitude_lognormality": false, "event_time_uniformity": false, "poisson_count": false}`.

### Replicate 3

- G2 event-count mean/variance per eligible recurrent patient: 9.56359649122807 / 20.91902352033931.
- Amplitude mean/CV: 15.04425896782195 / 0.5243481075014989; standardized lognormal KS statistic: 0.010235028150481273.
- Exclusions: `{"missing_recurrence_day": 0, "not_true_recurrence": 544, "zero_exposure": 0}`.
- Holm-adjusted p-values: `{"amplitude_lognormality": 1.0, "event_time_uniformity": 1.0, "poisson_count": 0.9968573111094926}`; reject at alpha 0.01: `{"amplitude_lognormality": false, "event_time_uniformity": false, "poisson_count": false}`.

### Replicate 4

- G2 event-count mean/variance per eligible recurrent patient: 10.15625 / 21.267123287671232.
- Amplitude mean/CV: 15.189853147077617 / 0.5022244696528406; standardized lognormal KS statistic: 0.016574415678465848.
- Exclusions: `{"missing_recurrence_day": 0, "not_true_recurrence": 488, "zero_exposure": 0}`.
- Holm-adjusted p-values: `{"amplitude_lognormality": 0.26459002938123843, "event_time_uniformity": 0.49312548498607245, "poisson_count": 0.26459002938123843}`; reject at alpha 0.01: `{"amplitude_lognormality": false, "event_time_uniformity": false, "poisson_count": false}`.

G1 recurrence counts and G2 event counts are separate quantities. G3 is included only as a comparison/contract control; this study makes no G3 mechanism or performance claim. Per-replicate diagnostics, exclusions, and eligible person-time are preserved in `results.json`.

All findings are limited to software fidelity under the frozen synthetic profile. They do not close profile calibration, verification bias, population realism, model performance, or clinical validation.
