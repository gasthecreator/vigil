# Model Card: Model K4 — deep irregular-time risk models (research module)

**Model identifier:** `MODEL-K4-DEEP-IRREGULAR`
**Version:** 2.0.0-research (replaces 1.0.0-alpha, whose evaluation was retracted)
**Maturity:** L0. Research code. **Not wired into ingestion, scoring, any API route or any ensemble.** `DRAFT-UNREVIEWED`.
**Governing documents:** `docs/ML_PROGRAM.md` §3.4 and §6 (S4); `docs/adr/0025-k4-rebuilt-and-not-claimed.md`; `experiments/EXP-K4-001/`.

## 1. What it is
Six forward-only encoder families that share one input convention and one training loop, in `packages/vigil-ml/vigil_ml/k4.py`:
GRU-D (decayed state and imputation), GRU-ODE-Bayes (deterministic encoder only: RK4 between visits with four sub-steps, GRU update at each visit; no observation likelihood and no KL term), Neural CDE (linear interpolation of the forward-filled path with time and count channels, Euler), a continuous-time transformer (causal attention with a learnable per-head exponential time bias, two layers), GRUwE (exponential decay of the state, source: evidence E24), and an irregular-time selective diagonal state-space model. Sizes: hidden width 16, 32 or 64.
Input per patient: up to 24 visits with ten log-scaled laboratory values (`clip(log(value / reference midpoint), -5, 5)`, midpoints fixed from `vigil_core.analytes`), their observed masks, visit days, six symptom grades divided by 4, and eight static values. The risk for a visit is read from the state at that visit, so a prediction never depends on a later visit (tested).
Masked-analyte pre-training code (hide 25 percent of observed laboratory values, predict them with a Huber loss) and a fine-tuning path are included for the study.
Export: safetensors (weights plus JSON metadata, no pickle) and ONNX (opset 17, probabilities, dynamic batch); exact safetensors round trip and ONNX parity within 1e-4 are tested for every family in `packages/vigil-ml/tests/test_k4.py`.
**Not built:** TabPFN-style prior-fitted networks, a contrastive pre-training objective, the adjoint and log-signature options of Neural CDE, and the GRU-ODE-Bayes variational observation model.

## 2. Intended use
Research on synthetic data: to study how deep irregular-time families compare with classical baselines as the labelled sample grows, whether masked-analyte pre-training helps, and whether size helps. **Not for clinical use.** No claim of clinical validity, regulatory clearance or benefit.

## 3. What was measured (synthetic data only; `experiments/EXP-K4-001/results.json`, `CONCLUSION.md`)
- **K4 is not claimed to beat classical models** (pre-registered H2 not met). At N = 1,000 labelled patients the strongest classical baseline (gradient boosting, B4) has IPCW AUC 0.7928; the designated deep family, GRU-ODE-Bayes, 0.786; the interval for their difference includes zero. At every smaller N no deep family reached the strongest baseline's mean AUC.
- **No pre-training is claimed or shipped** (pre-registered H1 not met: masked-analyte pre-training lowered AUC against training from scratch, -0.0201 with a Bonferroni interval wholly below zero, at N = 100). No pre-trained checkpoint exists.
- **Scale does not help** (pre-registered H3): large minus medium AUC -0.0041, interval [-0.0108, 0.0024]. Medium is the largest size to be used.
- The study's leakage canary averaged 0.448 (below the originally pre-registered range, which was relaxed on its lower side by amendment before the frozen run; `CONCLUSION.md` states this first). Under the original rule the study would have been void. Either way no claim is made.
- Cost on the study machine: about 7,400 to 22,500 parameters at medium; single-patient CPU latency about 0.3 to 1.2 ms except GRU-ODE-Bayes (about 5.8 ms) (`REPORT.md` section 8; machine-dependent).

## 4. Limits
Synthetic data and one simulator family (G1 training, G2 and G3 as shifted tests); one outcome (recurrence within 365 days); at most 1,000 labelled patients; two learning rates per arm; one pre-training objective; no real longitudinal laboratory corpus. Deep families are black boxes; any explanation tool would be auxiliary and not causal. Off the training generator every deep family was below B4 and K3.

## 5. What this card replaces
The earlier card quoted pre-training gains (+0.049 at N = 50, +0.038 at N = 100), a "Pareto optimal" medium size and latencies. They came from a study that returned literal dictionaries while the model learned nothing; they are retracted (`reports/ml/RETRACTED/README.md`) and must not be cited. It also listed a contrastive objective and a TabPFN-style encoder, neither of which exists.
