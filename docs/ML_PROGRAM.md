# Vigil — Machine Learning & Statistical Program

> Companion to `MASTER_PLAN.md` (v1.1). This document is **binding** and *deepens* MASTER_PLAN §6.1–6.3, §6.11–6.13 and §8; where it is stricter, it wins. Authority and change control: same as the Master Plan (executor files proposals; overseer amends).
> **Thesis:** Vigil's ML must be the strongest part of the product, and in this problem "strongest" does not mean "biggest model". It means (1) a correctly posed problem, (2) models that encode what is known about tumour-marker biology so they work with *sparse, irregular, noisy, informatively-missing* data, (3) uncertainty and alert error-rates that are *guaranteed*, not hoped for, even under repeated testing and distribution shift, (4) an evaluation science that survives the specific biases of screening/surveillance data, and (5) the discipline to report negative results. A deep network that scores 1.000 on its own generator is the opposite of this.

---

## 1. The hard problems (and why each is where the rigour must go)

| # | Problem | Why naïve ML fails here | Section |
|---|---|---|---|
| H-A | **Tiny, sparse, irregular, noisy sequences** (4–20 visits, gaps of months, 5–20 analytes, most missing) | Generic RNN/transformers overfit; no mechanism to share strength | §3.1 hybrid mechanistic state-space, §3.4 pre-training, §3.5 hierarchical pooling |
| H-B | **Repeated testing inflates false alarms.** An alert rule applied at every visit over 5 years has a far higher cumulative false-alarm rate than its per-visit α | A per-visit conformal/threshold guarantee says nothing about the *patient-level* false-alarm probability | §3.2 anytime-valid sequential detection |
| H-C | **Informative missingness (MNAR):** tests are skipped because of cost, access, or clinician suspicion | Imputation or ignoring masks injects bias; missingness itself is signal *and* confounder | §3.1, §3.3 (explicit observation models) |
| H-D | **Partial verification bias:** only patients who were imaged get a confirmed recurrence label; the rest are labelled "no event" by default | Models learn the *testing policy*, not biology; metrics are inflated | §4.2 |
| H-E | **Label delay, censoring, competing risks** (death, loss to follow-up, treatment change) | Binary classification at fixed horizons is biased | §3.3, §4.3 |
| H-F | **Lead-time and length bias:** earlier detection of an unchanged course looks like "better survival" | “Lead time gained” is not benefit; may even be harm (overdiagnosis, anxiety) | §4.5 |
| H-G | **Multi-lab, multi-method heterogeneity** (assay/analyser/lab differences, batch shifts) | A step change in the lab looks like disease | §3.5 lab harmonisation, M3 |
| H-H | **Treatment effects on markers** (chemotherapy suppresses/elevates; hepatotoxicity raises ALT; endocrine therapy shifts ALP) | Drug effects mimic or mask metastasis | §3.1 treatment-aware dynamics |
| H-I | **Synthetic→real gap and no real labels** | Everything looks great on your own simulator | §4.6, §5 |
| H-J | **Subgroup inequity** under small-N, shifted case-mix | Averages hide failures | §4.4, MASTER_PLAN 8.3 |
| H-K | **Decision value, not accuracy:** *when to test again* matters as much as *what the risk is* | Fixed-interval surveillance wastes scarce tests | §3.6 active sensing |
| H-L | **Causal questions** (does delay harm? does earlier action help?) | Observational confounding by indication | §3.7 |

---

## 2. Task definitions (formal)

Let patient *i* have baseline covariates **x**ᵢ, an irregular observation process {(tᵢⱼ, **y**ᵢⱼ, **m**ᵢⱼ)} (analyte values and observed-masks), exogenous inputs (treatments **a**ᵢ(t), symptoms **s**ᵢ(t), lab/method identifiers ℓᵢⱼ), a latent event time *T*ᵢ (distant recurrence, with site *S*ᵢ), and competing/censoring times.
- **T1 Site propensity** P(S | metastasis, **x**) — M1.
- **T2 Event hazard** λ(t | history up to t) and horizon risks Rₕ(t) = P(T ∈ (t, t+h] | history), h ∈ {3, 6, 12} months — M2.
- **T3 Change adjudication** P(real change | error | inconclusive | y_new, history, ℓ) — M3.
- **T4 Sequential detection** a stopping rule τ with *patient-level* false-alarm control: P₀(τ ≤ K visits) ≤ α_pt, maximising detection delay reduction — M2/M9.
- **T5 Next-test timing** policy π(history) → (when, which analytes/tests) maximising expected information/benefit per cost — M4/M2.
- **T6 Delay harm** E[harm | delay d, indication, subtype] — M7.
- **T7 Pre-training** representation learning over unlabeled lab sequences.
- **T8 Lab harmonisation** latent offsets/scales per (lab, method) — M3/M0.
- **T9 Calibrated, valid uncertainty** for T1–T5.

---

## 3. Model program

### 3.1 K1 — Hybrid mechanistic–neural state-space model ("Kinetic") *(the flagship; Frontier as a combination — verify prior art per MASTER_PLAN §13.7 before claiming novelty)*
**Idea:** Tumour markers and organ enzymes are *measurements of latent biology* with known kinetics. Model the latent state explicitly and let a neural network handle what the mechanism misses. This gives data-efficiency (few visits), interpretability (parameters are doubling time, shedding rate, clearance), principled handling of irregular times and missingness, and uncertainty by construction.
- **Latent state** zᵢ(t) = (B(t) tumour/micrometastatic burden by compartment [e.g., locoregional, bone, liver, lung, brain, other]; Mₖ(t) marker pool for each marker k; Oₒ(t) organ-damage state for each organ o).
- **Dynamics (SDE/ODE, continuous time):**
  - dB_c/dt = (g_c(θᵢ, treatment) − d_c(treatment)) · B_c + η_c(t), with **recurrence onset** as a latent seeding time τ_c per compartment (hazard from M1 prior × patient factors); growth g_c ≥ 0 with Gompertzian/logistic saturation option; therapy modifies g/d through time-varying inputs **a**(t).
  - dM_k/dt = Σ_c s_{k,c}·B_c − c_k·M_k + baseline_k(ℓ) (shedding s, clearance c_k), so CA 15-3 behaves as a *filtered integral of burden*, not as burden itself (this alone explains lag and why early rise is small).
  - dO_o/dt = coupling from B_c (infiltration/obstruction) and from drugs (hepatotoxic effects), driving ALT/AST/ALP/GGT/bilirubin/albumin etc. through organ-specific maps.
- **Observation model (per analyte):** y_{j,a} ~ LogNormal/Student-t(h_a(z(tⱼ)) + offset_{ℓ,a}, σ_a(ℓ)) with **method/lab offsets and scales** (T8), censoring for below-detection limits, plausibility-aware outlier component (mixture with a broad "error" distribution → feeds M3 directly), and an **observation-propensity model** P(m=1 | z, history, cost-band) to represent MNAR (selection model or shared-parameter model).
- **Neural components:** (i) a learned **residual drift** f_θ(z, a, t) bounded in magnitude (so it cannot replace the mechanism); (ii) an **amortised inference network** (recognition model) mapping the observed history to a posterior over patient-level parameters and the latent trajectory; (iii) optionally a learned correction to h_a.
- **Inference (compare, choose by evidence):** (a) amortised variational inference/structured VAE; (b) particle filter / unscented Kalman smoother for online filtering at each new visit (cheap, exact-ish); (c) NUTS (Stan/NumPyro) for gold-standard posteriors on small cohorts to *validate* (a)/(b); (d) simulation-based inference (neural posterior estimation, e.g., NPE/SNPE via the `sbi` ecosystem) because the likelihood is intractable under compartments + MNAR. **Simulation-based calibration (SBC)** and posterior-predictive checks are mandatory.
- **Outputs:** posterior over recurrence-onset time and compartments → horizon risks Rₕ(t) with credible intervals; posterior over doubling time and marker shedding; predictive distribution for the *next* observation (feeds M3 and M4); latent “burden” fan-chart for explanation (labelled *model-inferred, not measured*).
- **Identifiability discipline:** structural identifiability analysis (profile likelihood or differential algebra, documented) and *parameter recovery tests* on simulated data: recovery error/coverage reported per parameter, and a list of parameters declared unidentifiable under typical visit schedules (these get strong priors or are fixed).
- **AC:** SBC passes (rank statistics uniform within tolerance) on ≥ 3 simulator settings; posterior coverage of the true recurrence time ≥ nominal − 3 pp on held-out simulated patients; K1 beats the best *non*-mechanistic model on calibrated net benefit in the **low-data regime** (≤ 6 visits) with non-overlapping bootstrap CIs, or the elimination protocol records why not; ablations: no treatment input, no shedding kinetics, no MNAR model, no lab offsets, neural residual off/on.
- **Kill/fallback:** if full compartmental SDE is not identifiable/trainable, fall back to a *single-compartment* kinetic model with organ-weighted observation maps (still mechanistic), then to a linear-Gaussian state-space model (Kalman) with learned drift — each step by protocol.

### 3.2 K2 — Anytime-valid sequential detection *(guarantee that survives repeated looks)*
**Problem H-B.** An alert evaluated at every visit is a *sequential test*. Per-visit guarantees do not control patient-level false alarms.
- **Formulation:** for each patient, build a nonnegative **test supermartingale / e-process** Eₜ under the null “no recurrence-related change since baseline” using likelihood ratios or learned score functions from K1 (and from rule-based features), with *mixture* e-processes over alternative growth rates (so we do not need to know the rate). Alert when Eₜ ≥ 1/α_pt. **Ville's inequality** gives P₀(∃t: Eₜ ≥ 1/α_pt) ≤ α_pt for *continuous monitoring over any number of visits*. Complement with CUSUM/Shiryaev–Roberts charts and report **average run length to false alarm (ARL₀)** and **expected detection delay**.
- **Learned e-values:** train detectors to maximise power subject to validity; validity is checked empirically under the null on held-out patients and *simulated null trajectories with realistic lab noise, drift, treatment effects and lab shifts*; any detector that violates the bound under the stress suite is rejected.
- **Calibrated tiers:** `watch/review/urgent` correspond to different α_pt levels (e.g., higher α for watch). Operating points are chosen on validation data by the Section 8.6 procedure *and* these sequential guarantees (the two are reconciled in an ADR: sequential validity governs patient-level false-alarm control; conformal governs probabilistic risk-statement coverage).
- **Null-model misspecification:** because nulls are estimated, report robustness (worst-case over a family of nulls), and monitor realised alert rates in silent mode against the claimed α (an *alarm-rate audit*).
- **AC:** empirical patient-level false-alarm rate ≤ α_pt + tolerance across ≥ 5 null-stress scenarios; detection-delay reduction vs. threshold/velocity rules reported with CIs; unit tests of the e-process mathematics against closed-form examples; property tests (non-negativity, martingale property under simulated null).
- **Kill/fallback:** if learned e-processes lose too much power, ship the K1-likelihood-ratio e-process (simple, valid) or CUSUM with calibrated ARL₀.

### 3.3 K3 — Bayesian joint longitudinal–survival model *(gold-standard statistical comparator and a shippable model)*
- Multivariate mixed-effects (splines or GP) for analytes (with lab effects, treatment covariates) linked to a **cause-specific hazard** through current value, rate-of-change and cumulative-exposure associations; competing risks (death, loss to follow-up) modelled; MNAR via shared-parameter/selection extension; implemented in Stan or PyMC (and a fast approximation, e.g., two-stage/landmarking, for production).
- Purpose: (i) benchmark every ML model against the model statisticians would trust; (ii) a shippable, well-calibrated, interpretable option; (iii) a source of priors for K1.
- **AC:** convergence diagnostics (R-hat ≤ 1.01, ESS), posterior-predictive checks, calibration, dynamic prediction accuracy (time-dependent AUC/Brier), reported next to all models.

### 3.4 K4 — Deep irregular-time families and pre-training
- **Families:** GRU-D, GRU-ODE-Bayes, Neural CDE (with adjoint/log-signature options), continuous-time transformer (time-aware attention/RoPE-style continuous time), **GRUwE** [E11], S4/Mamba-style state-space sequence models adapted to irregular time, and **TabPFN-style prior-fitted networks** for static features.
- **Self-supervised pre-training:** masked-analyte/time modelling and contrastive objectives on (i) simulator-generated unlabeled sequences with *domain-randomised* parameters, (ii) MIMIC-IV lab series for cancer-coded stays (ICU caveat; access is a human action), (iii) any public longitudinal lab corpora found (research task). Study: label-efficiency curves (performance vs. number of labelled patients: 50, 100, 200, 500, 1000) with/without pre-training, and **scaling behaviour** (small/medium/large) to find where size stops helping — we expect it to stop early and must say so if it does.
- **Forward-only encoders** for forecasting; bidirectional only for retrospective smoothing tasks (e.g., audit).
- **AC:** every family evaluated under identical protocol (MASTER_PLAN 8.2–8.5) and included in the benchmark report; pre-training benefit quantified; compute/latency/memory reported per model.

### 3.5 K5 — Hierarchical pooling and lab harmonisation
- Hierarchical Bayesian model with partial pooling across **sites and labs** for baselines, offsets, scales and treatment effects; **batch-effect/“lab-shift” detection** (changepoints in offsets shared across patients tested in the same lab, which differentiate lab-change from disease-change — a key defence against false alarms).
- Reference-material anchoring where EQA/proficiency data exist (research task: EQA programme data for Nigerian labs).
- **Federated extension (M12):** the hierarchical model is the natural federated target (site-level parameters local, global hyper-parameters shared).
- **AC:** simulated multi-lab studies recover injected offsets with stated error; false-alarm rate under injected lab-shift is controlled; improved calibration on held-out *new site* vs. non-hierarchical models (the "new site" case is the one that matters).

### 3.6 K6 — Active sensing: *when to test next and which test* *(Frontier in this setting)*
- **Formulation:** choose the next visit time and test panel to maximise expected information gain about recurrence status (K1 posterior) or expected net benefit per unit cost, subject to resource constraints; compare against fixed-interval schedules (every 3/6 months), clinician-heuristic schedules, and risk-triggered schedules.
- **Methods:** Bayesian experimental design with posterior expected information gain via nested Monte-Carlo/variational bounds; budgeted adaptive policies; (optional, strictly offline and simulator-only) RL/bandit policies with conservative (pessimistic) off-policy evaluation. **Real patients are never exposed to an RL policy**; policies ship only as *suggestions* with the reasoning shown.
- **Value claim discipline:** reported as expected information gain/detection-delay/test-cost trade-off curves *in simulation*, labelled; clinical benefit is a hypothesis for T-Q/T-L tiers.
- **AC:** curves comparing policies across budgets with CIs; ablation by panel composition (cheap panel vs. full); policy stability tests; integration with M4 Test Ladder (cost/availability).

### 3.7 K7 — Causal analysis of delay and action *(for M7 and the evidence base)*
- **Target-trial emulation** on partner data (T-R) for radiotherapy delay: eligibility, time zero, treatment strategies, outcomes, confounders (indication, stage, subtype, performance status, comorbidity), handled with clone-censor-weight or marginal structural models, doubly-robust estimators, positivity diagnostics; **sensitivity analysis (E-values)** for unmeasured confounding; negative-control outcomes where possible.
- On simulation: verify estimators recover *known* causal effects under injected confounding by indication (so we know the method works before real data).
- **Fallback:** if real data are unavailable, M7 uses literature-derived priors with explicit uncertainty (E8), and the causal pipeline waits for T-R (documented, not stubbed: the code and simulation validation ship in Phase 7).

### 3.8 K8 — Model selection, ensembling and release policy
- Candidates K1–K7 + baselines go through **pre-registered selection** (MASTER_PLAN §13): primary metric = calibrated net benefit over the pre-specified threshold range *at fixed patient-level false-alarm control*; secondary = low-data performance, subgroup parity, latency, interpretability.
- **Stacking/ensembling** only if it improves calibrated net benefit with non-overlapping CIs *and* keeps validity guarantees (K2 applies to the final score); otherwise ship the single best model.
- **Release policy:** a model is shippable only with: model card; subgroup gates; validity (K2) tests; calibration; latency; reproducibility; signed bundle; PCCP entry.

---

## 4. Evaluation science (the part that makes claims believable)

### 4.1 Pre-registration
Every study S1–S10 (Section 6) has a committed `PREREG.md` *before* results exist: hypothesis, data, splits, metrics, thresholds, analysis plan, multiple-comparison control (Holm–Bonferroni or FDR across the pre-specified family), minimum effect, stopping/elimination rules.

### 4.2 Partial verification bias *(H-D)*
In real surveillance data, confirmation of recurrence depends on imaging, which depends on suspicion. Therefore:
- The **simulator must implement a verification mechanism** (probability of imaging as a function of symptoms, markers, access) and expose both *true* and *observed* labels, so we can measure how much each estimator is biased.
- Estimators/corrections to compare: complete-case (biased baseline), inverse-probability-of-verification weighting, Begg–Greenes-style corrections, EM/latent-class approaches, and model-based (K1 treats true status as latent and observation of imaging as an informative process). Report bias/variance versus ground truth in simulation.
- **Real-data protocol:** document the verification process at the partner site (what triggers imaging), include it as a covariate/design feature, and refuse to publish sensitivity/specificity without verification-bias analysis.

### 4.3 Time-to-event metrics under censoring and competing risks
IPCW-corrected time-dependent AUC/Brier; cumulative incidence calibration (not Kaplan–Meier 1−S when competing risks matter); landmarking with explicit landmark times; decision-curve analysis for survival data with censoring (net benefit with IPCW); calibration slope per horizon; time-varying calibration plots.

### 4.4 Equity and robustness evaluation
Subgroup tables with CIs (small groups use Bayesian shrinkage estimates, flagged); worst-group metrics; intersectional slices (e.g., TNBC × stage IV × young age) where N permits, with power statements; robustness to missingness patterns (MCAR/MAR/MNAR stress), lab shifts, unit errors, visit-schedule changes; adversarial data-entry suite (MASTER_PLAN 8.8).

### 4.5 Lead-time, length and overdiagnosis honesty *(H-F)*
- Report lead time as *“detection earlier than the best rule-based/clinical baseline, relative to a fixed definition of clinical recurrence”* — never as benefit.
- Quantify **overdetection risk** in simulation: fraction of alerts for patients whose indolent course would never have become clinically apparent within follow-up (the simulator contains such trajectories), and extra tests/imaging triggered per true recurrence found.
- State plainly that survival benefit of earlier detection in this setting is unproven (E1) and that Vigil's trials are designed to measure harms (false alarms, tests, anxiety) as outcomes, not just detection.

### 4.6 Synthetic→real discipline *(H-I)*
- **Cross-generator hold-out** (train on G1+G2, test on G3 with structurally different assumptions) and **assumption-perturbation sweeps** (vary shedding/clearance/noise/visit patterns beyond the training range) → performance-degradation curves. Report the *worst case*, not the best.
- **Identifiability-vs-realism check:** for the mechanistic model, fit K1 to simulated data from *non-mechanistic* generators (G3) to see how gracefully it degrades (model-misspecification stress).
- **Real-data cross-checks as soon as access exists:** (i) kinetics sanity on any public serial marker series; (ii) MIMIC-IV lab dynamics for plausibility priors; (iii) METABRIC/TCGA/SEER for M1 and for baseline-hazard shapes; (iv) partner data for everything.
- **Transfer experiments:** pre-train on sim → fine-tune on small real sets (when available) with label-efficiency curves.

### 4.7 Sample size and power for real validation
Use Riley et al. criteria for prediction-model sample size (events per parameter, shrinkage target, precision of calibration slope and of overall risk) and a simulation-based power analysis for sensitivity/false-alarm endpoints; compute the *minimum number of patients and events* needed per subgroup claim; commit as `docs/clinical/SAMPLE-SIZE.md` in Phase 8 so partner discussions are concrete.

### 4.8 Statistical testing hygiene
Paired bootstrap over patients (not visits) for all comparisons; ≥ 1,000 resamples; report effect sizes with CIs rather than p-values alone; DeLong-type or bootstrap tests for AUC differences; Holm/FDR across families; seeds ≥ 5 and random-split repetitions; no test-set reuse for selection (a **frozen final test set** per tier, touched once per pre-registered analysis, with an access log).

---

## 5. Data-regime ladder for ML work
1. **Sim-only development** (Phases 1–4): methods validated on *known truth* (parameter recovery, SBC, validity under nulls, bias correction).
2. **Public-data realism** (as access allows): priors, kinetics sanity, M1 real-data model, pre-training corpora.
3. **Real retrospective** (T-R): recalibration (never retraining from scratch without justification), subgroup validation, verification-bias analysis, target-trial emulation.
4. **Prospective silent** (T-Q): monitoring of claimed vs. realised alarm rates and calibration; adaptive conformal tracking.

Each result in each report carries its tier label; mixing tiers in one headline number is forbidden.

---

## 6. Pre-registered studies (each a self-contained work package with a report in `reports/ml/`)

| ID | Question | Primary comparison | Kill / fallback |
|---|---|---|---|
| S1 | Does mechanistic structure help when data are sparse? | K1 vs K3 vs K4 vs GBM at 3, 4, 6, 10, 20 visits | If K1 ≤ best non-mech at ≤ 6 visits → single-compartment K1 → Kalman → ship K3 |
| S2 | Is patient-level false-alarm control achieved under repeated looks? | K2 e-process vs per-visit threshold/conformal vs CUSUM | If power loss > pre-registered tolerance → likelihood-ratio e-process |
| S3 | How much do verification bias corrections matter? | Complete-case vs IPW vs latent-class vs K1 | Report all; ship the least-biased in simulation |
| S4 | Does pre-training help, and does scale help? | with/without; S/M/L | If not → no pre-training in production |
| S5 | Does hierarchical pooling + lab harmonisation reduce false alarms on new sites/labs? | K5 vs pooled vs per-site | If not → simple per-lab offsets |
| S6 | Does active sensing beat fixed schedules at equal test budget (simulation)? | K6 vs 3/6-month schedules vs heuristic | If not → ship risk-triggered schedule suggestions only |
| S7 | Does the Plausibility Adjudicator (M3) separate error from change? | RCV-only vs +delta vs Bayesian vs K1-predictive | If calibration fails → RCV + delta |
| S8 | Do causal estimators recover known delay effects under confounding? | MSM/CCW/DR vs naïve | If none do → literature priors only (no causal claims) |
| S9 | Cross-generator robustness | Train G1+G2, test G3; perturbation sweeps | Report degradation; widen priors/ensembles |
| S10 | Federated/DP utility cost | Federated vs central vs local (M12) | If > 3 pp loss → federated evaluation only |

---

## 7. ML engineering requirements

- **Compute plan** (`docs/ml/COMPUTE.md`): declare available hardware (assume developer laptop-class Apple Silicon/CPU unless stated), set model sizes and training budgets that run there with `device` abstraction (MPS/CUDA/CPU), and prepare — but do not require — a cloud-GPU run mode (container + job spec); budget requests are human actions (§17.3). If a study needs more compute than is available, scale the study design (fewer seeds with *documented* reduced power) rather than skipping it, and mark the limitation.
- **Stack:** PyTorch (+ `torchdiffeq`/`torchsde`, `torchcde`), JAX/NumPyro permitted for Bayesian components (ADR), Stan/PyMC for gold-standard posteriors, `sbi` for simulation-based inference, `lifelines`/`scikit-survival`/`pycox` for survival baselines, `MAPIE`/custom for conformal, `scikit-learn`/`xgboost`/`lightgbm` for classical, `Optuna` for tuning (nested protocols), `MLflow` + `DVC`, `ONNX`/`safetensors`, `Hydra`/Pydantic configs.
- **Determinism and reproducibility:** global seed management, deterministic flags, environment lock, dataset hashes, config snapshots; `make reproduce-ml` regenerates every number in `reports/ml/`; CI runs a *reduced-size smoke reproduction* (minutes) and a nightly *full reproduction*.
- **Performance engineering:** profile and budget inference (p95 < 300 ms; filter update < 100 ms per new visit on CPU); batched/vectorised simulation (≥ 10⁵ patients); ONNX export parity tests (max abs diff tolerances per output); numerical-stability tests for SDE/ODE solvers (step-size convergence, stiff-case handling), gradient checks (`torch.autograd.gradcheck` where applicable).
- **Testing ML code:** unit tests with analytic solutions (kinetics with closed forms), property-based tests (monotonicity: raising a marker, others fixed, must not lower risk unless the model learns an explicit, documented non-monotone effect), metamorphic tests, invariance tests (unit conversions; relabelling visit order must fail loudly), regression tests on frozen mini-benchmarks, leakage canaries (shuffled labels → chance; future-peek detector → fails), coverage + mutation testing on metric/validity code.
- **Monitoring in production:** feature/label drift, calibration drift, alarm-rate audit vs claimed α, posterior-predictive failure rate (how often new observations fall outside predicted intervals — a direct model-misspecification detector), abstention rate, latency; automatic *safe degradation* (fall back to simpler validated model) when monitors trip.
- **Security of ML:** safetensors/ONNX only; hash-verified bundles; input validation fuzzing; poisoning-resistance for any feedback loop (clinician feedback is reviewed, never auto-trained); membership-inference tests on any model trained on real data; DP accounting for federated runs.

---

## 8. Interpretability that is faithful

- **Mechanistic parameters are the first-class explanation** from K1 (doubling time, shedding rate, inferred onset window with credible interval) — a clinician can reason about them and challenge them.
- **Counterfactuals** computed by re-running the model with altered inputs (verified), plus **sensitivity analysis** of risk to each analyte and to the lab-offset assumption.
- **Attribution (IG/SHAP/occlusion)** only on non-mechanistic models; validated by deletion/insertion faithfulness and sanity checks (randomised-weights test); never presented as causal.
- **Explanation pipeline** feeds the M5 fact table; no explanation exists outside it.

---

## 9. Deliverables and phase mapping

| Phase | ML deliverables |
|---|---|
| **P1** | Simulator features required by this program: latent compartments with seeding times, marker shedding/clearance kinetics, organ-damage coupling, treatment effects on markers, lab/method offsets and scales, **verification mechanism with true vs observed labels**, **MNAR observation model**, label delay, competing risks, indolent trajectories (overdetection), error/outlier injection, null (no-recurrence) trajectories with realistic noise and treatment/lab shifts, visit-schedule variability; **ground-truth latent states exported** for recovery tests; ≥ 3 structurally different generators; calibration-target tests (MASTER_PLAN 6.13). |
| **P2** | Evaluation harness incl. IPCW metrics, DCA-survival, verification-bias estimators, subgroup/Bayesian-shrinkage reporting, frozen-test-set access log; classical baselines; K3 (joint model) and priors; studies S3, S9 (baseline), S1 (classical arms). |
| **P3** | K1 (all inference routes + SBC + identifiability), K2 (e-processes, CUSUM, validity stress suite), K4 (deep zoo + pre-training + scaling), K5 (hierarchical/lab harmonisation), K6 (active sensing), model selection and ensembling (K8), studies S1, S2, S4, S5, S6, S9; ONNX/safetensors export and runtime. M12 simulation (S10). |
| **P4** | M3 Adjudicator built on K1 predictive distributions + RCV/delta + K5 offsets (S7); M5 explanation facts from K1. |
| **P7** | K7 causal pipeline validated on simulation (S8); M7 harm model integration. |
| **P8** | Sample-size/power documents, pre-registration freeze, model cards, PCCP, monitoring runbooks. |
| **P9** | Real-data execution of the frozen plans; TRIPOD+AI report. |

**ML exit gates (added to the phase gates in MASTER_PLAN §14):** every study listed for the phase has `PREREG.md`, results JSON, report, and a decision record; SBC, validity, calibration and leakage canaries pass; every model's results appear in the benchmark with baselines; negative results are committed, not omitted; the **benchmark release** (`VigilBench`: simulator configs, splits, metric code, baseline results, leaderboard format) is publishable and reproduces from a clean checkout.

---

## 10. What would make us doubt ourselves (explicit stop-and-think triggers)
1. Any model achieves AUROC > 0.97 or Brier near 0 on anything resembling a realistic task → assume leakage/degenerate simulation until proven otherwise.
2. A deep model beats the joint model only on the *same* generator that produced its training data.
3. Calibration is good on average but fails for a subgroup, a lab, or a visit-count stratum.
4. Alert rates in the stress suite exceed the claimed α by more than tolerance.
5. Posterior-predictive failure rate rises when moving from G1/G2 to G3.
6. Parameter recovery fails for parameters the explanations depend on.
7. Gains vanish when verification bias is modelled.
8. Improvement is within bootstrap noise (then it is not an improvement).
Each trigger requires a logged investigation (`experiments/…/TRIAGE.md`) before any claim.

*End of ML Program.*
