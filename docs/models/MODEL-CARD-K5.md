# Model Card: Model K5 — laboratory harmonisation (research module)

**Model identifier:** `MODEL-K5-HARMONISATION-POOLING`
**Version:** 2.0.0-research (replaces 1.0.0-alpha, whose evaluation was retracted)
**Maturity:** L0. Research code. **Not wired into ingestion, scoring or any API route.** `DRAFT-UNREVIEWED`.
**Governing documents:** `docs/ML_PROGRAM.md` §3.5 and §6 (S5); `docs/adr/0024-k5-replaced-and-not-claimed.md`; `experiments/EXP-K5-001/`.

## 1. What it is
An estimator of proportional laboratory offsets on the log scale, for one analyte (CA 15-3 in the study). Offsets are identified only through patients who were tested at more than one laboratory. Implementation: `packages/vigil-ml/vigil_ml/k5.py`.
Model: `log y_ij = a_i + b_i t_ij + beta_{lab(i,j)} + e_ij`, patient intercept and slope fixed and eliminated by within-patient projection, `beta ~ N(0, tau^2)`, `tau` and `sigma` by REML, closed-form posterior. A laboratory with no connecting patient receives offset 0 and posterior sd `tau_hat`; a laboratory never seen in fitting is left unchanged (offset 0).
A CUSUM helper on one-step residuals with a calibrated threshold is included for the study; it is **not** a validated detector (section 3).
Export: safetensors (weights plus JSON metadata, no pickle) and ONNX (Gather, Exp, Div); parity to 1e-6 is tested in `packages/vigil-ml/tests/test_k5.py`.

## 2. Intended use
Research on synthetic data, to study whether partial pooling of laboratory offsets reduces false alarms of a fixed change rule. **Not for clinical use.** No claim of clinical validity, regulatory clearance or benefit.

## 3. What was measured (synthetic data only; `experiments/EXP-K5-001/results.json`, `CONCLUSION.md`)
- The pre-registered criterion for "K5 recovers at least half of the excess false alarms" was **not met** (0.520, 95% interval [0.438, 0.593]); the kill rule fired. K5 is not claimed to help.
- In the primary simulated cell an older mean-shrinkage method recovered more (0.609 [0.535, 0.677]); it does worse when laboratory and case mix are linked (0.304 against K5's 0.476).
- With few connecting patients for a new laboratory, K5 has lower error than per-lab fixed offsets (pre-registered H2 met), but per-lab fixed offsets are then worse than no adjustment at all.
- K5 95% intervals under-cover on the simulator's clinical trajectories (0.615 to 0.897 across six cells) and cover 0.949 when the model is exactly true (control), which points to model misfit with the simulated disease dynamics.
- The CUSUM could not be calibrated to the pre-registered false-alarm target on streams that contain disease progression (156.76 alarms per 1,000 residuals at the largest threshold tried); it is not a usable detector as specified.
- At the spread anchored by an external quality-assessment study (tau 0.07, a spread across laboratories, not a bias estimate), laboratory differences did not materially change the simulated rule's false alarms.

## 4. Limits
Synthetic data; proportional bias only; no scale or noise differences; one analyte; no reference-material anchoring; identification only through switchers; a single step change as the only temporal drift; the change rule is a study rule, not a clinical criterion. No real multi-laboratory data have been analysed.

## 5. What this card replaces
The earlier card claimed a 85.7 percent reduction in false alarms and a 34.2 percent Brier reduction on held-out sites. Those came from a study that subtracted the injected offset by hand and returned a literal; they are retracted (`reports/ml/RETRACTED/README.md`) and must not be cited.
