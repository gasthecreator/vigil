# EXP-M12-001: federated averaging and DP-SGD (M12), utility cost versus centralised training on a synthetic multi-site partition

**Status:** PRE-REGISTERED. This file is committed **alone**, before any M12 code and any run. Everything below is fixed at that commit; any later change is an *amendment* appended at the end with its reason and the `git diff`.

**Authority:** `docs/MASTER_PLAN.md` §6.12 and WP3.5, `docs/ML_PROGRAM.md` §3.5 (federated extension) and study S10 (question: "Federated/DP utility cost"; kill rule: "If > 3 pp loss → federated evaluation only"), `docs/MASTER_PLAN.md` §13 (elimination protocol). Data: **synthetic only**. Nothing here is evidence about real patients, real hospitals, or a legal privacy determination (NDPA/GDPR/HIPAA). (ε, δ)-DP is a bound on a mechanism, not a clearance.

**What I looked at before writing this file:** the retracted S10 (`reports/ml/RETRACTED/S10_MULTISITE_SYNTHETIC_TRIAL/`, literal site AUCs and a hard-coded "PASSED"), `vigil_sim.generators.generate_cohort` (it already takes `nominal_interval_days`), `vigil_ml.features.WindowedFeatureExtractor` (one feature row per visit; labels are prospective recurrence within a horizon), `vigil_eval.metrics.ipcw_time_dependent_roc_auc` and `survival_decision_curve_analysis`, E23 (between-laboratory spread used as a site offset scale), E26 (FedAvg) and E27 (DP-SGD). I did **not** train a federated or DP model, and I did not compare any of the four training paradigms.

## 1. Why this replaces the earlier S10
The earlier S10 is retracted. `scripts/run_benchmarks.py::run_study_s10` returned a literal dictionary (site AUCs 0.812, 0.774, 0.691, 0.798, 0.684 local; federated 0.821, 0.808, 0.786, 0.816, 0.778; utility drop 0.0068) and `render_s10_markdown` printed "H1 CONFIRMED … H3 CONFIRMED" and "Approve M12 Federated Training Architecture" regardless of data. No client trained. No privacy accountant ran. No bytes were withheld from a server.

This study trains the same model four ways on simulated sites and writes every number from the run.

## 2. Question
On a synthetic multi-site partition with site-specific analyser offsets, visit frequency, missingness and sample size, does (a) FederatedAveraging without DP, and (b) FederatedAveraging with DP-SGD, stay within 3 percentage points of **centralised** training on IPCW ROC-AUC at 365 days? How does each compare with **local-only** training, especially at the two smallest sites? What is the drop in calibrated net benefit at threshold 0.10 (MASTER_PLAN §6.12)?

## 3. Simulation (the truth is known)
**Five sites**, generated independently from `GeneratorType.G1_SMOOTH` (one generator, different seeds and sampling designs). Duration 730 days. `vigil_sim.generators.BaseGenerator.generate_cohort(num_patients, duration_days, nominal_interval_days)` is the only cohort constructor. After generation, two observation-level transforms (no generator internals, no `latent_*`):

1. **Analyser offset.** Every observed CA 15-3 and CEA value at site k is multiplied by `exp(β_k)`, `β_k ~ N(0, τ²)` with **τ = 0.07** (E23 sourced spread, as in EXP-K5-001). Other analytes are not shifted. Missing values stay missing.
2. **Extra missingness.** Independently of the simulator's own missingness, each remaining CA 15-3 and CEA value is set missing with probability `p_k` (below). ALP/GGT/AST/ALT are never additionally dropped.

| Site | Role (label only) | Train N | Test N | `nominal_interval_days` | `p_k` extra missing | `β_k` |
|---|---|---|---|---|---|---|
| A | urban tertiary | 400 | 200 | 45 | 0.00 | drawn |
| B | regional general | 200 | 100 | 90 | 0.05 | drawn |
| C | rural mission | 80 | 80 | 180 | 0.25 | drawn |
| D | private centre | 150 | 80 | 60 | 0.00 | drawn |
| E | community outreach | 80 | 80 | 120 | 0.20 | drawn |

`β_k` is drawn once per replication for each site (seed below) and applied to both that site's train and test observations. Test patients are a fresh `generate_cohort` with the same interval and `p_k`, never mixed into training. Total train N = 910, test N = 540 per replication.

**Landmark row (one per patient, so DP is patient-level).** From `WindowedFeatureExtractor.transform_cohort(..., horizon_days=365)`, keep, for each patient, the **last visit with day ≤ 365 and day ≥ 90**. Patients with no such visit are dropped (count reported). Features are exactly the extractor's columns except `patient_id`. Label `y` and follow-up time / event indicator are those the extractor already computed at that visit (prospective recurrence within 365 days; IPCW at evaluation). `latent_*` and `true_recurrence_*` are not read by the trainer; the extractor already uses `observed_recurrence_*` for labels, which is the observed clinical event, not a latent burden.

**Not claimed to match any Nigerian facility.** Names "rural mission" etc. are labels for the sampling design, copied in spirit from the retracted S10 so the replacement is comparable; the numbers (N, interval, p_k) are mine.

## 4. Model and training paradigms
**Model (identical in every arm).** A fully-connected network: input → Linear(d, 32) → ReLU → Linear(32, 1) → logit. Binary cross-entropy with logits. No dropout. Parameters are float32. Input dimension `d` is the extractor's feature count after dropping `patient_id` (fixed by the extractor; recorded in the result file). This is **not** B4 or K3. Those remain the shipped surveillance baselines (ADR-0007). This study asks whether *this* model, which can be trained with DP-SGD, loses utility when trained federated and with DP, relative to training it centrally. A **descriptive ceiling**: B4 (`GradientBoostingBaseline`) fitted on the pooled training landmarks, evaluated on the pooled test landmarks (one fit per replication). B4 is not federated and not DP.

**Optimiser (non-DP).** SGD, learning rate 0.05, minibatch 32, no momentum, no weight decay. Local training: 4 epochs. Central training: 4 epochs on the concatenated training landmarks. Initialization: every arm of a replication starts from the **same** initial weights (seed below).

**Paradigm L (local-only).** Site k trains on its own training landmarks for 4 epochs. The local model is evaluated on site k's test landmarks (primary local number) and, descriptively, on the pooled test set.

**Paradigm C (centralised).** One model trained on the concatenation of all five training sets. Evaluated on the pooled test set and, descriptively, on each site's test set.

**Paradigm F (FedAvg, E26).** Algorithm: for round `t = 1..R` with **R = 20**, every site (C_frac = 1) copies the server weights, runs **E = 2** local epochs of non-DP SGD, and returns its weights. The server sets `w ← Σ_k (n_k / n) w_k` with `n_k` the number of training landmarks at site k. All five sites participate every round. Communication is **in-process FederatedAveraging** (MASTER_PLAN §6.12 "Flower or equivalent"): there is no Flower server, no gRPC, no network. The algorithm is FedAvg; the transport is a function call. Reason, plainly: a simulation of the *algorithm* on synthetic sites does not need a network stack, and a network stack would make the study non-deterministic across machines. A unit test checks that the server update equals the n-weighted mean of the client weights.

**Secure aggregation (F and D).** Clients do not send raw weights. For each round, for every pair of sites (i, j), i < j, a shared random mask `m_{ij}` (the same shape as `w`, seed below) is added at i and subtracted at j, so `Σ_k (w_k + mask_k) = Σ_k w_k` exactly. The server is a function that accepts **only** the list of masked tensors and the list of `n_k`; it returns their n-weighted mean. A unit test checks that (i) the sum of masks is the zero tensor, (ii) the server function's source does not name `patient`, `analyte`, `X`, or `y`, (iii) replacing a client's unmasked weights with garbage, while leaving the masked payload unchanged, does not change the server output (the server never sees the unmasked tensor).

**Paradigm D (FedAvg + DP-SGD, E27) — the kill arm.** Same as F except every local step is DP-SGD (Abadi et al., Algorithm 1):
- lot size L = min(32, n_k);
- for each example in the lot, compute the gradient of the loss on that example, **clip** its ℓ2 norm to **C = 1.0** (`g ← g / max(1, ||g||_2 / C)`);
- average the clipped gradients;
- add isotropic Gaussian noise with standard deviation **σ C / L** per parameter (noise multiplier **σ = 1.0**), so the noise on the *sum* of clipped gradients is `N(0, (σ C)² I)`;
- take an SGD step with learning rate 0.05.
Privacy unit: **one landmark = one patient**. Accounting is per site, over that site's local DP-SGD steps across all 20 rounds (2 epochs × ceil(n_k / L) steps per round × 20 rounds). The accountant is the **moments accountant** of E27 (log-moments of the privacy-loss random variable of the sampled Gaussian mechanism, converted to (ε, δ) by Markov). **δ = 1 / N_train_total** with N_train_total = 910 (fixed). The ledger records, per site, (ε̂, δ, σ, C, steps, q = L/n_k). The headline privacy number is **max_k ε̂_k** at this δ. A unit test of the accountant, using the paper's full-text example (q = 0.01, σ = 4, δ = 10⁻⁵, T = 10000), must recover ε in **[1.15, 1.40]** (the paper reports ≈ 1.26). If the test fails, the accountant is wrong and the study does not run.

**Not built, and not evaluated here:** Flower as a process; Opacus as a library (DP-SGD is implemented in `vigil_ml/m12.py` and tested; adding Opacus would pin a second autodiff stack to a specific torch build); secure hardware; user-level DP beyond one-row-per-patient; membership-inference on real records (there are none); a legal opinion.

## 5. Endpoints
All on the **frozen test landmarks**, never used for training. Pooled = concatenate the five sites' test landmarks. IPCW ROC-AUC at horizon 365 days via `vigil_eval.metrics.ipcw_time_dependent_roc_auc`. Calibrated net benefit at threshold **0.10** via `vigil_eval.metrics.survival_decision_curve_analysis` (the 0.10 is a study threshold, not a clinical cut-off). ECE with 10 equal-count bins of predicted risk.

Per replication the script writes:
- pooled AUC, Brier, ECE, NB@0.10 for C, F, D, and for B4;
- per-site AUC and NB@0.10 for L, C, F, D;
- D_F = AUC_C − AUC_F and D_D = AUC_C − AUC_D (pooled);
- Dnb_D = NB_C − NB_D at 0.10 (pooled);
- local gap at small sites: G_CE = mean_{k in {C,E}} (AUC_C on site k − AUC_L on site k);
- equity gain: mean_{k in {C,E}} (AUC_F on site k − AUC_L on site k), and the same for D;
- privacy ledger (paradigm D);
- number of patients dropped for lack of a landmark visit, per site;
- wall time of the replication.

## 6. Hypotheses and decision rules
Multiplicity: primary family **{H2, H3}**, paired bootstrap over replications (B = 2000, seed 20261220), percentile intervals at level `1 − 0.05/2`. H1 and H4 are descriptive with 95 percent intervals and support no claim.
- **H1 (local silos, descriptive).** G_CE has lower bound > 0.10. (The retracted S10's H1; kept as a stated check, not a claim.)
- **H2 (FedAvg without DP stays within 3 pp of central).** D_F point estimate ≤ 0.03 **and** the Bonferroni upper bound of D_F is ≤ 0.03.
- **H3 (FedAvg + DP-SGD stays within 3 pp of central) — the S10 kill.** D_D point estimate ≤ 0.03 **and** the Bonferroni upper bound of D_D is ≤ 0.03.
- **H4 (net benefit, descriptive; MASTER_PLAN §6.12's metric).** Dnb_D point and 95 percent upper bound, reported; "within 3 pp of NB" is stated as met or not on the same rule as H3 but is **not** in the primary family (net benefit at 0.10 is typically much smaller than 0.03 in absolute units in this simulator, so a 3 pp rule on NB would be almost automatically met; that is why AUC is the kill metric, matching ML_PROGRAM S10 and the retracted study).

**Kill and fallback (ML_PROGRAM S10 / MASTER_PLAN §6.12).** If H3 fails, M12 is **not** claimed as a training architecture; what ships as research code is **federated evaluation only** (a site can score a shipped model locally and share aggregate metrics). If H3 holds, M12 is still only a **simulation claim** on this model and this partition: not wired into any pipeline, not a pilot, not a legal privacy claim. A pre-registered failure is an acceptable outcome (§13).

**Leakage canary (can void the study).** In every replication, paradigm D is re-run with **σ = 100** (same C, same steps) on the same data. Canary statistic = pooled AUC of this run. **VOID if the mean over replications is above 0.60.** A DP-SGD run with enormous noise must not still discriminate; if it does, information is reaching the model some other way. One-sided on purpose.

## 7. Seeds, development and frozen evaluation
- **Development replications** `r ∈ {0, 1, 2}`, base `s_r = 1100 + 100 r`. **Frozen replications** `r ∈ {0..9}`, `s_r = 20261220 + 100 r`. Per replication: site-A train seed `s_r`, A test `s_r+1`, B train/test `+2/+3`, C `+4/+5`, D `+6/+7`, E `+8/+9`; β draws `+10`; model init `+11`; SGD noise `+12`; secure-agg masks `+13`; DP Gaussian `+14`; canary `+15`.
- Debugging uses only development replications. The development file is committed.
- **The frozen run is executed once.** If code changes afterwards, the old result stays committed and an amendment and a new run are added. R, E, σ, C, learning rate, epochs, architecture, site table, τ, threshold 0.10 and the hypotheses are fixed here.
- Every number in the report is written by `experiments/EXP-M12-001/run.py`; none is typed.

## 8. Invariants tested before the frozen run (`packages/vigil-ml/tests/test_m12.py`)
1. **FedAvg identity:** the server's new weights equal the n-weighted mean of the client weights to 1e-6.
2. **Secure aggregation:** sum of masks is 0; server source does not name patient-level data; the server output is unchanged when unmasked client tensors are scrambled.
3. **No raw-data egress:** an AST scan of `m12.py` and of the runner's federated path forbids writing patient rows, feature matrices or labels to disk, sockets, or HTTP; the only values that cross the client/server boundary in code are tensors of model weights (masked) and the integers `n_k`.
4. **DP-SGD clip:** a single-example gradient with ℓ2 norm 10 is clipped to C = 1.0 (norm 1.0 ± 1e-5).
5. **Accountant:** the E27 numerical example recovers ε ∈ [1.15, 1.40] at δ = 10⁻⁵.
6. **Determinism:** the same seed yields identical weights for paradigm C (and identical masked sums for F).
7. **Causality / labels:** scrambling `latent_*` columns of the cohort tables does not change X, y, or any trained weight (the trainer never reads them).
8. **No pickle** in `m12.py` or the runner.
9. **Canary on a toy:** with σ = 100, 50 steps, planted-label data of 200 patients, AUC is ≤ 0.60.
10. **Planted signal:** on a toy where y is a linear function of one feature plus tiny noise, paradigm C and paradigm F (2 sites, 10 rounds) both reach AUC > 0.85, and paradigm D with σ = 0.3 reaches AUC > 0.70.

## 9. What will be reported regardless of outcome
Strongest baseline first (B4 pooled, then C, F, D, then L by site); the canary; the privacy ledger; H1–H4 as met or not with numbers from `results.json`; per-site tables; run time. If H3 fails, `experiments/EXP-M12-001/CONCLUSION.md` is the elimination record (what was tried, the §13.3 checklist, what ships instead — federated evaluation only — what would change the decision). The word "infeasible" is not used unless §13.2's three serious attempts are met.

## 10. Not in scope (stated as limits, not hidden)
Real multi-site data; Flower as a deployed server; Opacus as a dependency; NDPA/GDPR legal analysis; membership inference on real records; DP at visit-level (we use one row per patient); federated training of B4/K3/K5; a pilot (MASTER_PLAN §6.12 step 4 is a human action after governance approval, H-116); secure hardware; differential privacy against an adversary who already has the simulator.

## Amendments
_None at the time of this commit._
