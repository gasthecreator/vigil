# EXP-K5-001: lab harmonisation (K5), hierarchical pooling against per-lab offsets and no adjustment

**Status:** PRE-REGISTERED. This file is committed **alone**, before any K5 code, any multi-lab simulator code and any run. Everything below is fixed at that commit; any later change is an *amendment* appended at the end with its reason and the `git diff`.

**Authority:** `docs/ML_PROGRAM.md` §3.5 (K5) and study S5 (kill rule: "if not, simple per-lab offsets"), `docs/MASTER_PLAN.md` §13 (elimination protocol). Data: **synthetic only**. Nothing here is evidence about real patients or real laboratories.

## 1. Why this replaces the earlier S5
The earlier S5 (`reports/ml/S5_HARMONISATION/`, moved to `reports/ml/RETRACTED/S5_HARMONISATION_V1/` by the commit that follows this one) is retracted for two reasons found by reading `vigil_ml/harmonisation_k5.py::run_study_s5`:
1. The "harmonised" arm subtracts the injected offset by hand (`harm_obs = raw_obs - 5.5`), so it measures the arithmetic of subtraction, not the estimator.
2. `new_site_brier_reduction_pct` is the literal `34.2`, and the "34.2% lower Brier score on held-out clinical facilities" sentence is a constant.
In addition, the old estimator shrinks a laboratory's **mean value** toward a global population median. A laboratory's mean also reflects its case mix, so the estimator cannot tell "this lab reads high" from "this lab sees sicker patients". That is a flaw of the design, tested here as a secondary scenario.

## 2. Question
When patients are tested at several laboratories whose results differ by a proportional bias, does partial pooling of laboratory offsets (K5) reduce false alarms of a fixed change rule, without hiding true recurrences, compared with (a) doing nothing, (b) estimating each laboratory's offset on its own (per-lab fixed offsets), and (c) the earlier mean-shrinkage method? Does a changepoint detector on laboratory streams detect a step change in a laboratory within a stated delay at a stated null false-alarm rate?

## 3. Simulation (the truth is known)
- **Clinical layer:** `vigil_sim.generators.get_generator(GeneratorType.G1_SMOOTH, seed).generate_cohort(num_patients=800, duration_days=730.0)`; only the observed CA 15-3 column `ca_15_3` (non-missing, positive) is used. The `latent_*` columns are never read.
- **Laboratory layer (new, `vigil_sim/multilab.py`, written after this file):** `L_net = 6` network laboratories (ids 0 to 5). Home laboratory drawn from probabilities (0.25, 0.20, 0.20, 0.15, 0.10, 0.10). A fraction `π_sw` of patients with at least 3 CA 15-3 observations switch, at a visit index drawn uniformly from 1 to n_obs-2 (zero-based, so at least one result before and one after), to a laboratory drawn uniformly from the other five. Every result is multiplied by `exp(β_ℓ)`, with `β_ℓ ~ N(0, τ²)` independent per laboratory (a proportional bias on the log scale). There is no other laboratory effect (no scale or noise differences) in the primary design.
- **Where τ comes from:** E23 (`docs/EVIDENCE.md`): across laboratories within reagent classes the robust CV of CA 15-3 ranged from 6.48 to 7.63 percent, so **τ = 0.07 is the sourced scenario**. It is a spread of results between laboratories, not a bias estimate, and it is from a Chinese programme. **τ = 0.15 and τ = 0.30 are assumptions** (stress scenarios), labelled as such everywhere.
- **Grid (6 cells):** τ ∈ {0.07, 0.15, 0.30} × π_sw ∈ {0.10, 0.30}. Every cell is reported; no cell is dropped.
- **Case-mix scenario (secondary, one cell):** τ = 0.15, π_sw = 0.30, but the home laboratory depends on stage: laboratories 0 and 1 receive 80 percent of stage III and IV patients (split equally), laboratories 2 to 5 share the rest, and the converse for stage I and II patients (0.80 to laboratories 2 to 5, the remainder to 0 and 1).
- **New-site scenario:** two additional laboratories (ids 6 and 7) with τ as in the cell. `k ∈ {0, 3, 10, 30}` switching patients per new laboratory are added to the *training* cohort (patients who have results at the new laboratory and at one network laboratory); the new laboratories have no other patients in training. The evaluation cohort then contains patients whose home laboratory is a new one (800 patients: 50 percent home 6, 50 percent home 7, no switching).
- **Calendar time (for the detector only):** each patient receives an entry day uniform on [0, 540]; calendar day = entry + visit day.

## 4. Estimators (all on `z = log(CA 15-3)`, fitted on the training cohort only)
Model for every method that uses patient trajectories: `z_ij = a_i + b_i t_ij + β_{ℓ(i,j)} + ε_ij`, `ε ~ N(0, σ²)`, with patient intercept `a_i` and slope `b_i` treated as fixed effects and eliminated by within-patient projection (the offsets are identified only through patients who are tested at more than one laboratory).
- **Pooled (no adjustment):** `β̂ = 0`.
- **Legacy mean shrinkage (the earlier K5):** `β̂_ℓ = w_ℓ (mean z at ℓ − global mean z)`, `w_ℓ = n_ℓ / (n_ℓ + 15)`, `n_ℓ` = number of results at ℓ (the earlier module's rule, on the log scale).
- **Per-lab fixed offsets:** the projected least-squares estimate with a minimum-norm gauge (components not connected to the rest by switching patients are estimated as zero); standard errors from `σ̂²`.
- **K5 (partial pooling):** `β_ℓ ~ N(0, τ²)`; `σ²` and `ρ = τ²/σ²` by restricted maximum likelihood on the projected model (`ρ` searched on a log grid of 400 points from 1e-4 to 1e2, then refined by bounded scalar optimisation); `β̂ = (Z̃ᵀZ̃ + I/ρ̂)⁻¹ Z̃ᵀ r̃`, posterior covariance `σ̂² (Z̃ᵀZ̃ + I/ρ̂)⁻¹`. A laboratory with no connecting patient gets `β̂ = 0` and posterior sd `τ̂`.
- **Oracle (upper bound, not a method):** the true `β_ℓ`.

## 5. Endpoints
**E1 offset contrasts.** For every pair of network laboratories, the error of the estimated contrast `β̂_a − β̂_b` against `β_a − β_b` (gauge-free). Reported: RMSE over pairs, per method, per cell, per replication. For new sites: contrasts between the new laboratory and each network laboratory, by `k`. Interval coverage: share of pairs whose 95 percent interval contains the truth (K5 and fixed; "not estimable" where the fixed estimator has no connecting patient).
**E2 downstream rule (primary).** Offsets fitted on the training cohort are applied to a **separate evaluation cohort** of 800 patients generated with the same laboratory structure and the same `β_ℓ`. Fixed rule R, chosen here and not tuned: at the j-th CA 15-3 result (j ≥ 2) of a patient, alert when `h_ij - mean(h_i1..h_i,j-1) ≥ log(1.25)`, where `h = z - β̂_ℓ`. The 25 percent rise is a rule chosen for this study, **not a clinical criterion**. Per method:
- `FAR` = share of patients without a true recurrence event (`true_recurrence_event == False`) with at least one alert.
- `Sens` = among patients with a true recurrence and at least one CA 15-3 result in the 180 days before the true recurrence day, the share with at least one alert at a result in that window (the count excluded for having no such result is reported).
- `recovered fraction` = `(FAR_pooled − FAR_method) / (FAR_pooled − FAR_oracle)`, defined only where `FAR_pooled − FAR_oracle ≥ 0.01` (otherwise "lab effect not material here, no claim").
**E3 detector.** One laboratory (id 2) gets a step change `δ ∈ {0, 0.10, 0.20, 0.30}` (log units) from calendar day 365. On each laboratory stream in calendar order the residual is `r = h - mean(previous h of the same patient)`, with `h` the K5-harmonised value; `r` is standardised by the MAD-based SD of the residuals of the calibration streams; one-sided CUSUM `S_n = max(0, S_{n-1} + (r_n/σ_r − 0.5))` alarms when `S_n ≥ h*`. `h*` is the smallest value on {2, 2.25, ..., 15} for which the calibration streams (null, no shift, 20 calibration replications, seeds below) have at most 1 alarm per 1,500 residuals. Reported per `δ`: alarms per 1,000 residuals on the null laboratories, power (alarm in the shifted laboratory within 180 calendar days of day 365, and not before), median and interquartile range of delay in calendar days and in laboratory residuals.
**E4 withholding (descriptive, no hypothesis).** In the shifted laboratory at `δ = 0.20`: FAR and Sens of rule R among patients with results at that laboratory after day 365, with and without withholding alerts from the detector's alarm time onward.

## 6. Hypotheses and decision rules
Multiplicity: the primary family is {H2 at k=3, H2 at k=10, H3} and uses paired-bootstrap percentile intervals at level `1 − 0.05/3` (Bonferroni), bootstrap over replications, B = 2000, RNG seed 20261101. Everything else is descriptive, with 95 percent intervals, and is not used for a claim.
- **H1 (the problem is material).** In a cell, `FAR_pooled − FAR_oracle ≥ 0.05`. Reported for all six cells. If it fails in the sourced cell (τ = 0.07), that is stated plainly as "lab bias of the sourced size does not materially change this rule in this simulator".
- **H2 (partial pooling beats per-lab offsets when data are scarce).** For new laboratories with `k ∈ {3, 10}` in the cell τ = 0.15, π_sw = 0.30: mean over replications of (RMSE_fixed − RMSE_K5) of the new-laboratory contrasts has a paired-bootstrap interval whose lower bound is > 0. No claim at `k = 30`; at `k = 0` both give contrast zero and the question is coverage only.
- **H3 (K5 recovers most of the excess false alarms).** In the cell τ = 0.15, π_sw = 0.30: `recovered fraction` of K5 ≥ 0.5 with the lower bound of its interval ≥ 0.5, **and** `Sens_K5 ≥ Sens_oracle − 0.03` (point estimate).
- **H4 (calibrated intervals).** In every cell, K5 95 percent interval coverage of network contrasts lies in [0.90, 0.99].
- **H5 (detector).** At `δ = 0.20`: power ≥ 0.8 and median delay ≤ 120 calendar days; on the null laboratories, alarms per 1,000 residuals ≤ 1.0 (the calibration target is 0.67; the allowance reflects that calibration and evaluation are different samples).
**Kill and fallback (from `docs/ML_PROGRAM.md` study S5):** if H3 fails, or K5 does not beat the per-lab fixed offsets on E2 (recovered fraction not larger with a non-overlapping interval) *and* H2 fails, K5 is **not** claimed to help; the recommendation becomes simple per-lab fixed offsets where connecting patients exist and no adjustment otherwise. A pre-registered failure is an acceptable outcome (§13).

## 7. Seeds, development and frozen evaluation (no tuning on evaluation data)
- **Development replications** `r ∈ {0..9}`: training cohort seed `100 + 10 r`, evaluation cohort seed `101 + 10 r`, laboratory-layer seed `102 + 10 r`. All debugging uses only these. The development results file is committed.
- **Calibration replications** (detector threshold only) `r ∈ {0..19}`: seeds `500000 + 10 r` (+1, +2 as above), no shift.
- **Frozen evaluation replications** `r ∈ {0..99}`: seeds `20261101 + 10 r` (+1, +2). The frozen run is executed **once**. If code changes afterwards, the old result stays committed and a new amendment and run are added. Hyper-parameters (ρ grid, the 25 percent rule, CUSUM slack 0.5, 1-per-1,500 target) are fixed here and are not changed after seeing any result.
- Every number in the report is written by the script (`experiments/EXP-K5-001/run.py`); none is typed.

## 8. Invariants tested before the frozen run (`packages/vigil-ml/tests/test_k5.py`)
1. With noise-free data and a connected design the REML/GLS solution recovers the injected contrasts to numerical precision.
2. As `ρ → 0` all offsets go to 0; as `ρ → ∞` K5 equals the per-lab fixed estimator.
3. Relabelling laboratories permutes the estimates; adding a constant to all true offsets changes no contrast estimate.
4. A laboratory with no connecting patient receives offset 0 and posterior sd `τ̂`.
5. Export to safetensors (no pickle) and to ONNX reproduces the harmonised values of the fitted model (parity tolerance 1e-6).
6. The study script cannot read any `latent_*` column and cannot read the true offsets inside an estimator (checked by an AST test of the estimator module and by a test that scrambles the true offsets and shows the estimates do not change).

## 9. What will be reported regardless of outcome
All six cells for every endpoint, strongest baseline first; the development file; H1 to H5 as passed or failed with numbers from `results.json`; the case-mix scenario; run time. If H3 or the kill rule fires, `experiments/EXP-K5-001/CONCLUSION.md` is the elimination record (what was tried, the §13.3 checklist, what ships instead, what would change the decision).

## 10. Not in scope
Real laboratory data; reference-material (EQA) anchoring; scale and noise differences between laboratories; changes in laboratory over calendar time other than the single step; per-analyte offsets other than CA 15-3; integration of K5 into the ingestion pipeline. Each is stated as a limit, not hidden.

## Amendments
(none)
