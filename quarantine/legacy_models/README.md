# Quarantined Prototype Models: DEPRECATED-INVALID-LABELS

> **WARNING:** These model artifacts are quarantined per `docs/MASTER_PLAN.md` §14 WP0.3 and §15 (Defects A1, A2, A3, A8).
> **DO NOT USE IN ANY RUNTIME OR CLINICAL PATHWAY.**

## Reason for Quarantine
1. **Defect A1 (Circular Ground Truth):** Trained on an internal `is_anomaly` generator flag rather than a clinical event horizon.
2. **Defect A2 (Spurious Performance):** Val ROC-AUC of 1.000 was a symptom of extreme label leakage.
3. **Defect A3 (Acausal Architecture):** PyTorch BiLSTM processes future steps within the window, violating prospective forecasting requirements.
4. **Defect A8 (Unsafe Deserialization):** `.pkl` serialization represents an arbitrary-code-execution vector.

## Replacement Plan
These artifacts have been permanently removed from the application runtime path.
Valid models will be introduced in Phase 2 (classical baselines) and Phase 3 (safetensors/ONNX causal models) adhering to strict clinical event horizons without data leakage.
