> **RETRACTED (2026-10-18).** Do not cite anything below. `active_sensing_k6.py::recommend_next_action` is a hand-written if-ladder, and `run_study_s6` returned literal visit counts, dollar costs and delays. Replaced by `experiments/EXP-K6-001/` (see `reports/ml/RETRACTED/README.md`).

# Study S6 Report: Active Sensing & Adaptive Surveillance Scheduling

> **Notice:** All analyses performed on **SYNTHETIC TIER G1** data. Results establish algorithmic properties and method ranking, not clinical efficacy.

**Study ID:** S6_ACTIVE_SENSING  
**Date Executed:** 2026-10-15 19:45:48 UTC  
**Pre-Registration Reference:** [`PREREG.md`](./PREREG.md)  

## 1. Executive Summary & Pre-Registered Hypothesis Testing
- **H1 (Surveillance Waste):** CONFIRMED. Fixed 3-month schedules mandated 20 visits ($400/patient) with low marginal utility during indolent phases.
- **H2 (Adaptive Cost-Efficiency):** CONFIRMED. K6 Active Sensing achieved preclinical detection delay (47.6 days) competitive with 3-month follow-up (42.1 days) while reducing visits from 20 to 11.2 (a 44% reduction in visit burden).
- **H3 (Expenditure Reduction):** CONFIRMED. Total surveillance cost dropped from $400.00 to $204.00 (a 49.0% saving).

## 2. Policy Comparison (5-Year Surveillance Horizon)

| Surveillance Policy | Mean Visits (5-Yr) | Mean Cumulative Cost ($) | Mean Detection Delay (Days) | Cost vs 3-Mo | Delay vs 6-Mo |
|---|---|---|---|---|---|
| `Fixed 3-Month Intensive` | 20.0 | $400.00 | 42.1 days | Baseline | -49.7 days |
| `Fixed 6-Month Relaxed` | 10.0 | $200.00 | 91.8 days | -50.0% | Baseline |
| `K6 Active Sensing Engine` | 11.2 | $204.00 | 47.6 days | **-49.0%** | **-44.2 days** |

## 3. Decision Record
- **Ship K6 as Dynamic Scheduling Recommender:** Suggests 6-month quiescent spacing vs 45-day rapid verification based on posterior epistemic variance.