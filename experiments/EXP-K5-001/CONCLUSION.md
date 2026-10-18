# EXP-K5-001 conclusion (SYNTHETIC): K5 partial pooling is not claimed to help; the pre-registered kill rule fired

**Decision.** The pre-registered criterion H3 was **not met**, so under the kill rule of `PREREG.md` section 6 K5 is **not claimed to improve** the false-alarm behaviour of a change rule, and nothing built on it is claimed either. `vigil_ml/k5.py` stays in the repository as a research module with export and parity tests; it is not wired into ingestion, scoring or any route. This is a failed pre-registered criterion, not a finding that harmonisation is infeasible (see "What this is not").

All numbers below are copied from `results.json` / `REPORT.md`, which `run.py --frozen` wrote (100 frozen replications, one run; the committed files are that run). Synthetic data only.

## Strongest baseline first
In the primary cell (tau 0.15, switching 0.30) the **legacy mean-shrinkage method recovered more of the excess false alarms than K5**:

| Method | Recovered fraction of the excess FAR (95% interval) | Contrast RMSE (log units) | FAR | Sens |
|---|---|---|---|---|
| legacy mean shrinkage | 0.609 [0.535, 0.677] | 0.1270 | 0.0262 | 0.8326 |
| K5 | 0.520 [0.438, 0.593] | 0.1329 | 0.0304 | 0.8335 |
| per-lab fixed offsets | 0.337 [0.218, 0.443] | 0.1560 | 0.0390 | 0.8330 |
| no adjustment | (reference) | 0.2132 | 0.0548 | 0.8336 |
| oracle | 1 by definition | 0 | 0.0078 | 0.8328 |

Legacy has the larger recovered fraction in all four non-case-mix cells with tau at least 0.15 (0.537, 0.609, 0.714, 0.772 against K5's 0.130, 0.520, 0.328, 0.656; `REPORT.md`, E2 table). At tau 0.07 with switching 0.30 every method has a negative recovered fraction (legacy -0.458, K5 -0.048, per-lab fixed -1.485), i.e. none of them beats doing nothing there. It loses its advantage in the **case-mix scenario**, the one built to break it: legacy 0.304 [0.187, 0.407], per-lab fixed 0.310 [0.182, 0.424], K5 0.476 [0.388, 0.556]. In the independent-assignment design the legacy method's mean offsets are unbiased because a laboratory's patients are not systematically sicker; when stage and laboratory are linked it confuses case mix with bias, as `PREREG.md` section 1 said it would. That second comparison is one scenario at one setting.

## Hypotheses (as computed in `REPORT.md`)
- **H1 (problem is material, FAR gap pooled vs oracle at least 0.05).** Met only at tau 0.30 with switching 0.30 (0.0806). **Not met in the sourced cell** (tau 0.07: 0.0048 and 0.0125): *lab bias of the sourced size does not materially change this rule in this simulator.* At the primary cell it is 0.0470, just below 0.05.
- **H2 (K5 beats per-lab offsets for new laboratories).** Met: k = 3 RMSE(fixed) - RMSE(K5) = 0.3535, Bonferroni interval [0.2972, 0.4140]; k = 10 0.1403 [0.1129, 0.1710]. Context the table needs: at k = 3 the RMSE without adjustment is 0.2041, K5 is 0.1887 and per-lab fixed offsets are 0.5423, so with three connecting patients per new laboratory the fixed estimator is much worse than doing nothing and K5 is only slightly better than doing nothing.
- **H3 (K5 recovers at least half of the excess false alarms, interval lower bound at least 0.5, Sens within 0.03).** **Not met.** Point 0.520, 95% [0.438, 0.593], Bonferroni lower 0.412. Sens 0.834 vs oracle 0.833 (that part holds).
- **H4 (K5 95% interval coverage in [0.90, 0.99] in every cell).** **Not met in any of the six cells**: 0.615, 0.719, 0.687, 0.825, 0.817, 0.897 (tau 0.07/0.10, 0.07/0.30, 0.15/0.10, 0.15/0.30, 0.30/0.10, 0.30/0.30).
- **H5 (detector: power at least 0.8, median delay at most 120 days, at most 1.0 null alarms per 1,000 results).** **Not met.** The calibration target could not be reached: no threshold on the pre-registered grid gives at most 1 alarm per 1,500 residuals; at the largest threshold (15) the calibration streams alarm 156.76 times per 1,000 residuals. On the null laboratories the evaluation rate is 153.836 per 1,000. The power (1.0) and delay (median 9.59 days at delta 0.20) are therefore not evidence of a working detector: the chart alarms constantly.
- **Kill rule:** H3 failed, so it fires. (K5 also did not beat per-lab fixed offsets with a non-overlapping interval on E2: K5 [0.438, 0.593] and fixed [0.218, 0.443] overlap.)

## Diagnosis (MASTER_PLAN §13.3)
| Item | Finding |
|---|---|
| Leakage | Not found. The estimator module imports no simulator and takes four arrays (`test_estimator_module_cannot_see_simulator_or_truth`); the runner passes exactly patient, visit day, laboratory, value (`test_estimator_inputs_are_exactly_patient_day_lab_value`); `latent_*` is never read (`test_runner_never_touches_latent_columns`). |
| Bug in the estimator | Tested for, none found: noise-free recovery to 1e-8, rho limits, relabelling, unconnected laboratory, safetensors and ONNX parity (`packages/vigil-ml/tests/test_k5.py`). The **control scenario** (the K5 model exactly true, simulator visit schedule) gives K5 contrast RMSE 0.0203 against 0.2132 without adjustment, tau_hat 0.150 (true 0.15) and coverage 0.949 (fixed 0.955). So the estimator behaves as designed when its model holds. |
| Train/test mismatch | **Yes, probably the cause of H4 and of the weaker K5 recovery.** The control's coverage is 0.949 whereas the same estimator on the simulator's clinical trajectories covers 0.615 to 0.897. The K5 model assumes log-linear patient trajectories; the simulator's recurrence dynamics are not log-linear, and a switcher whose marker moves around the switch looks like a laboratory offset. This is a hypothesis supported by the control; no experiment here isolates it (for example by varying the amount of non-linearity). |
| Insufficient signal in the simulator | Partly: at the sourced spread (tau 0.07) the pooled rule is almost as good as the oracle (H1), so there is little to recover. |
| Label noise / under-training | Not applicable. |
| Mis-calibration (detector) | The diagnostic table in `REPORT.md` shows the calibration alarms come from patients with a recurrence: among residuals of patients without a recurrence event the alarm rate is 0.00 per 1,000 at every threshold from 5 to 60 (0.91 at 2), against 156.76 per 1,000 for all residuals at threshold 15. A CUSUM on one-step residuals cannot tell a laboratory shift from disease progression when progression is in the stream. This diagnostic uses the simulator truth and was added by Amendment 2; it explains the result and chooses nothing. |

## E4 (descriptive)
At delta 0.20, with alerts from the shifted laboratory withheld from the detector's alarm time onward: FAR falls from 0.2965 (1978/6671) to 0.0141 (94/6671) but Sens falls from 0.6761 (4302/6363) to 0.0039 (25/6363). The alarm is never lifted, so withholding removes the true alerts with the false ones. This is a reason not to build withholding on this detector.

## What ships instead (fallback ladder)
- `PREREG.md` section 6 names "simple per-lab fixed offsets where connecting patients exist, and no adjustment otherwise". **The data do not support deploying that either at the sourced spread**: at tau 0.07 per-lab fixed offsets have a higher FAR (0.0390 at switching 0.30, 0.0269 at 0.10) than no adjustment (0.0204, 0.0126). The honest state is: no harmonisation is shipped to any pipeline; the earlier module's claims are withdrawn (old S5 retracted, model card rewritten); K5 remains a research module at maturity L0.
- No claim in the repository depends on K5.

## What this is not
- Not evidence that laboratory harmonisation is infeasible: MASTER_PLAN §13.2 asks for three distinct serious attempts before "infeasible" may be written. Here a single K5 formulation (one prior family, one rule, one analyte, one simulator) was tried against two baselines. The word is not used.
- Not evidence about real laboratories or patients.

## What would change the decision
Real multi-laboratory data with patients who changed laboratory; reference-material (EQA) anchoring that does not rely on switchers; a K5 variant with a trajectory model fitted to real CA 15-3 dynamics instead of per-patient log-linear fits; a detector that models patient trajectories jointly with laboratory effects rather than one-step residuals. Each would need its own pre-registration.

## Everything changed after the pre-registration (the complete list)
1. `PREREG.md` Amendment 1 (commit `5b33ed1`), before any run: the new-site evaluation cohort (the original design would have shown nothing).
2. `PREREG.md` Amendment 2 (commit `3a19429`), after the first development run, before the frozen run: reporting additions only (calibration attainment flag, the diagnostic table, the control scenario). No hypothesis, grid, rule, slack or threshold was changed. The first development result (`dev_results_v1_pre_amendment2.json`) is kept unchanged. It showed that the calibration target was unattainable and the runner had silently returned the last grid value; the second development file (`dev_results.json`) shows it explicitly.
3. The engine, simulator layer, runner and tests were committed in `4d77bee` after the PREREG (they were written after it, by design). One of my own tests had wrong arithmetic (it expected at most 6 of 20 streams to alarm when the calibration target implies about 0.63 of them would); it was corrected before the frozen run.
4. The first development run was made with `k5.py` before `cusum_alarm_count` was factored out; the factoring changes no value.
5. Retraction work done after the run (no effect on the study): the old S5 moved to `reports/ml/RETRACTED/S5_HARMONISATION_V1/`, references removed from `scripts/run_benchmarks.py`, `scripts/verify_phase.py`, `reports/ml/BENCHMARK_REPORT.md` and `reports/ml/results.json` (the last two edited by removing the S5 entry, not by re-running the benchmark runner, to avoid unrelated cross-platform numeric drift).

## Disclosures
- Development replications 0 to 9 were used for debugging and for the two disclosed observations above; the frozen seeds were run once.
- The replication-level bootstrap uses the pre-registered B = 2000 and seed 20261101; the "recovered fraction" intervals are for a ratio of replication means.
- Rule R is a study rule, not a clinical criterion. The 25 percent rise, the 0.5 slack and the 1 per 1,500 target were chosen before any result and not changed.
