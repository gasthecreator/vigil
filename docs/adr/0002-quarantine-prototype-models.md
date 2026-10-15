---
status: accepted
date: 2026-10-14
decision-makers: Gideon Sanni (Product Owner), Gemini (Executor)
consulted: Claude (Overseer)
informed: Contributors
---

# 0002. Quarantine of Prototype Machine Learning Models (Defects A1, A2, A3, A8)

## Context and Problem Statement
An audit of the initial prototype models revealed fundamental methodological and security defects:
1. **Defect A1 (Circular Training Label):** The prototype Model B was trained using the synthetic generator's internal `is_anomaly` flag on the final draw, rendering the task trivially separable and causing extreme data leakage.
2. **Defect A2 (Meaningless Headline Metrics):** A validation ROC-AUC of 1.000 was reported as a success rather than investigated as label leakage. Model A reported $R^2 = 0.7884$ against an arbitrary vector synthesized by the generator.
3. **Defect A3 (Bidirectional LSTM for Longitudinal Forecasting):** Model B utilized a bidirectional LSTM that processes both past and future sequence steps across the window, invalidating temporal causality for prospective forecasting.
4. **Defect A8 (Pickled Model Serialization):** Model weights and scalers were stored as `.pkl` files (`baseline_model.pkl`, `feature_scalers.pkl`), exposing execution environments to arbitrary code execution upon deserialization.

## Decision Drivers
- Truth over impressiveness: scientific invalidity must never be dressed up as production functionality.
- Security: zero execution of untrusted pickle streams in production or testing paths.
- Temporal causality: forecasting models must strictly respect historical sequence bounds.

## Considered Options
- **Option 1: Retain prototype models with disclaimer notices**
- **Option 2: Quarantine prototype models away from default runtime execution paths**
- **Option 3: Immediate retrain with partial heuristics**

## Decision Outcome
Chosen option: **Option 2: Quarantine prototype models**.
- Prototype `.pkl` and `.pt` weights are moved to `quarantine/legacy_models/` marked as `DEPRECATED-INVALID-LABELS`.
- The default runtime path in `apps/api` does NOT deserialize pickle files or load the circular BiLSTM.
- Model A requests in Phase 0 fall back to calibrated literature/SEER priors (E12).
- Model B requests in Phase 0 execute a safe, transparent biomarker velocity check with explicit synthetic and non-diagnostic disclaimers, or return an explicit `model_status: "quarantined_pending_phase_3"` response.
- Validated prospective models will be developed in Phase 2 (classical baselines) and Phase 3 (safetensors/ONNX causal models) using leakage-free clinical event horizons.

### Confirmation
Enforced by `scripts/check_claims.py`, removal of pickle imports in production inference paths, and `apps/api` test assertions.
