# Model card: M3 biomarker plausibility adjudicator

**Identifier:** `MODEL-M3-PLAUSIBILITY-ADJUDICATOR`

**Implementation:** [`packages/vigil-ml/vigil_ml/m3.py`](../../packages/vigil-ml/vigil_ml/m3.py)

**Contract:** [`docs/ml/M3-M5-CONTRACT.md`](../ml/M3-M5-CONTRACT.md)

**Evidence:** E9 is `SECONDARY`; see [`docs/EVIDENCE.md`](../EVIDENCE.md) and [`docs/evidence/E9.md`](../evidence/E9.md).
**Validation status:** Synthetic contract and simulator evaluation only. No clinical calibration or patient-level validity is established.

## Intended behavior

With prior observations, M3 evaluates one new positive biomarker measurement and returns three model-conditional scores—`p_real`, `p_error`, and `p_stable`—plus one of `explained`, `needs_repeat`, or `escalate`. With no prior observation, it returns `abstain`, null probabilities, and `insufficient_history`; it does not use the current result as its own baseline. It rejects non-finite values, invalid CVs/priors, and histories that include the current or a future observation. It never returns `dismissed`. These scores are conditional on the explicit likelihood and prior assumptions below; they are not validated probabilities of recurrence or laboratory error for a patient.

Observation, OCR-confirmation, batch, and HL7 ingestion run M3 only for records marked synthetic or while the server is in isolated silent-shadow mode. For records marked non-synthetic, the visible path abstains with `clinical_validation_unavailable`; stored research scores are suppressed from patient, caregiver, and risk-history routes. Integration is not evidence of clinical validity. Do not use an M3 score or action to diagnose, rule out recurrence, defer evaluation, or replace clinician judgment.

## Model assumptions

The current synthetic assumptions are versioned in [`m3_assumptions_v1.json`](../../packages/vigil-ml/vigil_ml/models/m3_assumptions_v1.json), with implementation and loader in `vigil_ml.m3`. They define a geometric-mean baseline; log-normal stable noise; a persistent increase drawn from the configured ratio range; and three weighted gross-error modes. The default priors, thresholds, illustrative CV inputs, and inter-lab variation are contract assumptions, not estimates learned from a clinical cohort. The [`EXP-M3-001 protocol`](../../experiments/EXP-M3-001/PREREG.md) registers a sensitivity audit on new core-v4 simulator seeds; no sensitivity result exists until its single registered run is recorded.

The reference-change calculation uses the conventional formula documented in E9. The CA 15-3 and CEA variation values are retrieved from a Westgard/Ricós secondary compilation; they are therefore labelled `SECONDARY` in the registry. The desirable analytical CV values derive from half the listed within-subject CV and are also marked `SECONDARY`. A desirable CV is not a measurement of the actual analyzer's precision.

## Evaluation

The pre-registered S7 report is [`reports/ml/S7_PLAUSIBILITY/REPORT.md`](../../reports/ml/S7_PLAUSIBILITY/REPORT.md). On its contract-matched synthetic cohort, M3 has near-perfect discrimination and calibration because the evaluator samples from the model's own assumptions; this is mathematical contract evidence only.

On the separate `vigil-sim` cohort, S7 reports gross-error AUROC 0.8583 (95% CI 0.8090–0.9015), manifest-recurrence-rise AUROC 0.4961 (0.4394–0.5570), all-post-recurrence AUROC 0.4910 (0.4370–0.5474), zero-dismissal policy compliance 100%, and poor calibration (real-change ECE 0.2021; error ECE 0.3960). The pre-registered gradual-recurrence targets were not met. M3 is a single-measurement heuristic under a synthetic contract; it is not a longitudinal recurrence detector.

## Limitations and required work

- S7's `vigil-sim` results do not support real-change detection; gradual recurrence is near chance.
- The likelihood's population-centered error mode and priors are fixed assumptions, not fitted to an intended clinical population.
- E9 values come from a secondary compilation. Analyzer-specific precision, population transport, and the clinical target are not established.
- Synthetic contract tests do not estimate patient-level calibration, sensitivity, specificity, or clinical utility.
- The input-domain checks cover finite values, nonnegative CVs, normalized priors, positive measurements, and strict temporal ordering; they do not establish that the assumptions fit any clinical population.
- The no-history abstention and fourth action extend the current P4 contract; `PROP-CORE-ML-M3-ABSTENTION.md` requests overseer review. Acceptance tests remain unchanged.
- The added abstention plain-language copy is an implementation draft and requires clinical review before any patient-facing release.
- M5 copy for scored outcomes now describes conditional model components and asks the care team to interpret results; its modified goldens do not substitute for clinical review.

M3 remains research-only. Any clinical promotion requires a registered target estimand, justified parameters, independent data, calibration and subgroup evaluation, and review of every serving path.
