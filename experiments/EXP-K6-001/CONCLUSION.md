# EXP-K6-001 conclusion (SYNTHETIC): H1 and H2 met in this simulator; H3 not met; K6 is a suggestion with reasons shown, not a clinical claim

**Decision.** Under the kill and fallback rules of `PREREG.md` section 6 (and `docs/ML_PROGRAM.md` study S6):
- **H1 met** (Bonferroni upper bound of K6 minus the fixed frontier, averaged over the two named budgets, is below 0): in this simulator, at equal assumed cost, the K6 frontier is earlier than the frontier of the 24 fixed schedules. The observed margin is **2.3 days**.
- **H2 met** (same comparison against the 48-arm risk-triggered frontier): the observed margin is **0.8 days**.
- **H3 not met** (cost saving at the delay of the 3-month schedule): point 0.312, Bonferroni interval [0.175, 0.425]; the lower bound is not above 0.25, so the 25 percent saving is **not claimed**.
- **Because H1 and H2 both hold**, the pre-registered fallback is **not** "risk-triggered suggestions only". It is: **K6 is still only a suggestion with its reasoning shown, and only a simulation claim; no clinical benefit is claimed.** `vigil_ml/k6.py` is a research module (maturity L0). Nothing in this study wires it into a pipeline, route or ensemble. ESMO guidance (E25) does not recommend routine markers in asymptomatic patients.

All numbers below are copied from `results.json` / `REPORT.md`, which `run.py --frozen` wrote (frozen run 2: 20 replications, one run after amendment 4; code hash `a5c0a82cb49870ed`, the hash of the committed `k6.py`, `k6_engine.py`, `surveillance.py` and `run.py`). Synthetic data only. Costs are in assumed units, not money. Delay is days from true clinical recurrence to detection (negative = earlier). Frozen run 1 is kept in `run1_superseded/` and is **not** the decision: its planner used a defective panel table (amendment 4).

## A caveat that comes first: the 2.3-day margin sits on a 60-day symptomatic-presentation effect
In scenario A (primary), the named 3-month fixed schedule `F(91, P2)` has mean delay **−61.6 days** (`REPORT.md` section 2): most of the delay cohort is already found by the unscheduled symptomatic-presentation rule, which is an assumption of `PREREG.md` section 3 (no presentation delay, imaging taken to be positive, the same for every policy). K6's 2.3-day margin is on top of that. The pre-registered H1 rule had **no minimum effect size**, only "upper bound of the interval below 0", so H1 is met as written. It is not evidence that 2.3 days would matter to a patient. Scenario B (screening only, no symptomatic presentation; descriptive) has S1 = −12.4 days [`REPORT.md` section 4], which shows that most of the room for a scheduling policy in this simulator is in catching people who would otherwise wait for symptoms.

The leakage canary (K6 with shuffled-label hazard minus the fixed frontier, 100 fits) is 0.0 days, 95% interval [−0.0, 0.1]. **Not void** under the one-sided rule of section 6.

## Strongest baseline first
At the two named budgets on G1, scenario A (`REPORT.md` sections 2 and 3):

| Budget | Cost units | Fixed-frontier delay | K6-frontier minus fixed | Risk-triggered-frontier; K6 minus it |
|---|---|---|---|---|
| B13 (`F(91, P2)`) | 34.66 | −61.6 days | **−3.0 [−3.1, −2.9]** | −1.7 [−1.8, −1.3] |
| B26 (`F(182, P2)`) | 19.09 | −59.7 days | **−1.6 [−1.8, −1.5]** | **0.0 [−0.2, 0.2]** |
| Bmid | 25.72 | (interpolated) | −2.3 [−2.5, −2.2] | −0.6 [−0.8, −0.4] |

H1 is the mean of the two fixed-frontier contrasts (−2.3 days, Bonferroni [−2.4, −2.2]). H2 is the mean of the two risk-triggered contrasts (−0.8 days, Bonferroni [−1.0, −0.6]). **At B26, K6 and the risk-triggered frontier are not distinguishable** (interval includes 0). The stage heuristic is 0.7 days *later* than the fixed frontier at its own cost (28.73 units) (`REPORT.md` section 3).

At equal cost near B13, K6 (`w = 1.6`, cost 33.52) has overdetection 46.8 per 100 patient-years against 32.5 for `F(91, P2)` (`REPORT.md` section 2): the earlier detection is not free.

## Hypotheses (as computed in `REPORT.md`)
- **H1.** S1 = −2.3 days, Bonferroni [−2.4, −2.2], dropped draws 0.000; rule: upper bound < 0; **met**.
- **H2.** S2 = −0.8 days, Bonferroni [−1.0, −0.6], dropped draws 0.000; **met**.
- **H3.** S3 = 0.312, Bonferroni [0.175, 0.425], dropped draws 0.013 (below the 5 percent drop cap); rule: lower bound > 0.25; **not met**.
- **Canary:** not void (above).

## Descriptive results that bear on why (no claim; all from `REPORT.md`)
- **Panel composition.** `k6_P1` (liver enzymes only; interval still chosen) matches `k6_free` at every listed budget (both −3.0 / −1.6 / −2.3 days against the fixed frontier). `k6_P2` is smaller (−0.9 / −0.2 / −0.8). `k6_P3` is at or behind the fixed frontier (−0.0 / +0.5 / +0.3). So in this simulator the K6 margin is **interval timing with the cheap panel**, not the addition of CA 15-3 or CEA. The panel table's detection sensitivity is 1.000 for P1, P2 and P3 (`REPORT.md` section 9): alert rule A includes a symptom-grade ≥ 2 clause that does not depend on the panel, so once a detectable patient is symptomatic enough, every panel alerts. That is a property of the rule and of the simulator, not evidence that tumour markers detect.
- **Information.** `k6_prior` (static covariates and time since surveillance began; no laboratory history) is −0.4 / −0.2 / −0.1 days against the fixed frontier: near zero. The laboratory history is what the 2.3-day margin uses.
- **Cross-generator** (hazard, thresholds and panel table trained on G1 only): G2 S1 = −1.1 [−1.3, −0.9], S2 = −1.5 [−1.7, −1.3]; G3 S1 = −0.6 [−0.6, −0.5], **S2 = +0.3 [0.1, 0.4]** (`REPORT.md` section 6). On G3, K6 is *later* than the risk-triggered frontier at equal cost. No claim is transported off G1.
- **Cost-unit sensitivity** (stored runs rescored, K6 not re-planned): S1 stays −2.3, −2.2, −2.3 days under visit 0.5, visit 3, and geometric panel units {1, 2, 4} (`REPORT.md` section 7).
- **Calibration.** ECE of G(182) on random-schedule test rows is 0.0113 (`REPORT.md` section 8).
- **Stability.** For `w = 1.6`, knots perturbed by up to 0.02: the interval moves by more than one grid step in 0.004 of decisions; the panel changes in 0.000 (14,586 decisions per replication).
- **Not built, as declared in the PREREG:** posterior expected information gain by nested Monte Carlo on K1; reinforcement learning; conservative off-policy evaluation.

## Diagnosis (MASTER_PLAN §13.3)
| Item | Finding |
|---|---|
| Leakage | Not found. Policy code never names a truth column (`test_policy_code_never_names_a_truth_column`); scrambling evaluation-only arrays does not change any decision or cost (`test_evaluation_only_arrays_do_not_change_any_decision_or_cost`); causality holds (`test_decisions_before_a_day_do_not_depend_on_data_from_that_day_on`). The canary is not void. |
| Bug in the planner / engine | Tested for: monotone interval in G for a single panel, limits in `w`, availability, hazard range, export round-trip, planted signal, planner stability, and (amendment 4) panel-table counting (`packages/vigil-ml/tests/test_k6.py`). Frozen run 1 *did* have a bug (panel table counted only visits that had already missed detection, so `s_π = 0` floored to 0.02). That is why there is a run 2. The amendment-4 check held: 1,440 fixed + 60 heuristic + 2,880 risk records are bit-identical to run 1; training-row count 56,630.9 and false-alert probabilities are identical; only sensitivity (0.000 → 1.000) and the K6 / canary arms changed. |
| Train/test mismatch | Possible off G1: on G3, H2-style S2 changes sign (K6 later than risk-triggered). The hazard is an XGBoost fit to G1 random schedules. |
| Insufficient signal in the simulator | Partly, in scenario A: symptomatic presentation already finds most of the delay cohort ~60 days before clinical recurrence, so a scheduling policy has little left to do. Scenario B is the setting where the margin is large, and it is not the primary. |
| Under-training / grid | The hazard hyper-parameters were fixed in the PREREG (no tuning). The `w` grid was extended downwards by amendment 3 after development replications showed the original grid did not reach the budgets (the one change section 7 permits). |
| Detection mechanism | Common to every policy. K6 only chooses the next interval and panel. The 2.3-day margin is therefore a scheduling margin under a shared alert rule, not a better detector. |

## What ships instead (fallback ladder)
- No K6 schedule is recommended for a real patient. The module is not imported by the API or the web app. The registry entry states that any claim is a **simulation claim only**.
- H3 failed, so a "25 percent cheaper at the same delay" sentence is not written anywhere as a result.
- E25 recommendation 8d (laboratory tests and tumour markers not recommended in asymptomatic patients) stands; this study does not overrule it. The ablation `k6_P1` matching `k6_free` is consistent with markers adding nothing in this simulator under rule A.
- The S6 fallback "risk-triggered schedule suggestions only" is **not** selected, because H2 met. What is selected is the stricter sentence already in the PREREG: suggestion with reasons, simulation only. Risk-triggered remains a documented comparator (and on G3 it is the better of the two).

## What this is not
- Not evidence that active sensing, information-gain design or reinforcement learning are infeasible. MASTER_PLAN §13.2 asks for three distinct serious attempts before "infeasible" may be written. Here one planner (finite-horizon closed form of amendment 1), one hazard (XGBoost plus isotonic), one alert rule and one simulator were tried. EIG and RL were declared out of scope before any run. The word is not used.
- Not evidence about real patients, real prices, real attendance or real laboratories.
- Not a finding that 2.3 days of mean delay is clinically meaningful. The H1 rule did not ask that question.
- Not a finding that K6 beats the risk-triggered policy at every budget or generator: at B26 the interval includes 0, and on G3 the sign reverses.

## What would change the decision
Real follow-up series with known visit dates, test panels, prices or price-bands, and recurrence dates (a partner extract; access is a human action, H-115); a detection rule that does not already include a high-sensitivity symptom clause, so that panel composition can matter; imperfect attendance; a pre-training or information-gain objective on K1 (not built); a minimum effect size in the hypothesis. Each would need its own pre-registration.

## Frozen run 1 (defective; kept, not the decision)
Run 1 (`run1_superseded/`, code hash `097dfe9cc67ffb47`) printed H1 −2.0 days [−2.1, −1.8], H2 −0.5 [−0.7, −0.2], H3 0.288 [0.170, 0.370], canary not void, and a panel table with sensitivity 0.000 / 0.000 / 0.000. Those numbers came from a planner that used `s_π = 0.02` for every panel (amendment 4). They are not quoted as results. The decision above is run 2.

## Everything changed after the pre-registration (the complete list)
1. **Code written after the PREREG, by design:** `vigil_ml/k6.py`, `k6_engine.py`, `vigil_sim/surveillance.py`, `packages/vigil-ml/tests/test_k6.py`, `experiments/EXP-K6-001/run.py` (commits `db73548` and `d2f0f87`).
2. **PREREG amendments:**
   - A1 (commit `7bb0ebd`), before any K6 code and before any run: the original per-day objective chose the *longest* interval for a patient already believed ill; replaced by the finite-horizon closed form. Hypotheses, grids (original `w`), costs and kill rules unchanged.
   - A2 (commit `99dbb8e`), before any run: bootstrap draws that cannot be computed are dropped (hypothesis not met if more than 5 percent dropped); canary uses per-replication frontiers; cost-unit sensitivity is a rescore.
   - A3 (commit `9c5a275`), after development replications with the original `w` grid (`dev_results_grid1.json`, committed as it was): the cheapest K6 arm cost ~74 units against budgets 34.5 and 19.0, so no hypothesis was covered. The one change section 7 permits: `w` grid halved at its lower end eight times (17 values). Development replications with the extended grid are `dev_results.json`.
   - A4 (commit `f8181fd`), after frozen run 1: panel table now counts every training visit. Run 1 files moved unchanged to `run1_superseded/`. I had read run 1's verdicts before finding the defect; that is disclosed in the amendment. Frozen run 2 uses the same seeds. A unit test was added that fails on the old counting.
3. **Commit hygiene slip.** The K6 reproducibility verifier was staged in the same commit as frozen run 1 (`ab9a869`), so that commit is not "results alone". History not rewritten. Run 2's results are this file's sibling commit, results only.
4. **Retraction work** (no effect on the study): `active_sensing_k6.py` deleted; `run_study_s6` raises and points here; the hard-coded S6 renderer is gone; the K6 model card is rewritten without the retracted dollar figures and visit counts.

## Disclosures
- Development replications 0 to 2 were used for debugging, for the coverage check that justified amendment 3, and for the post-amendment-4 coverage and panel-table check. The frozen seeds of run 2 were run once.
- I looked at run 1's verdicts before amendment 4. The decision rule applied to run 2 is the pre-registered one; hypotheses, thresholds, grids (including the `w` grid of A3), model settings, costs, kill rules, seeds and the bootstrap were not changed after seeing run 1.
- The deep / hazard arms are not compared bit-for-bit across machines in CI: `scripts/verify_study_reproducibility.py` re-derives the aggregate and the report from the stored records and re-runs the fixed and heuristic arms of frozen replication 0. `VIGIL_VERIFY_K6_FULL=1` re-runs the whole replication (opt-in; tree-ensemble floats are platform-dependent).
