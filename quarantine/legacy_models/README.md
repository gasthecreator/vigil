# Quarantined Prototype Models: DEPRECATED-INVALID-LABELS

> **WARNING:** These legacy prototype model artifacts are quarantined per `docs/MASTER_PLAN.md` §14 WP0.3, §15 (Defects A1, A2, A3, A8), and Overseer Condition C4 (`docs/progress/VERDICT-P0-P1.md`).
> **DO NOT USE IN ANY RUNTIME OR CLINICAL PATHWAY.**

---

## 1. Reason for Quarantine & Defect Registry
1. **Defect A1 (Circular Ground Truth):** Trained on an internal `is_anomaly` generator flag rather than a clinical event horizon.
2. **Defect A2 (Spurious Performance):** Val ROC-AUC of 1.000 was a symptom of extreme label leakage.
3. **Defect A3 (Acausal Architecture):** PyTorch BiLSTM processes future steps within the window, violating prospective forecasting requirements.
4. **Defect A8 (Unsafe Deserialization):** `.pkl` serialization represents an arbitrary-code-execution vector.

---

## 2. Purge of Serialized Binaries from Working Tree
Per Overseer Condition C4, the binary files have been purged from the active working tree to prevent security risks, arbitrary code execution vectors, and repository bloat. They are preserved in git history at commit `45cd94b` (and `fa48736`) with the following immutable cryptographic checksums:

| Artifact Name | Former Location | SHA-256 Digest | Size | Historical Commit |
|---|---|---|---|---|
| `baseline_model.pkl` | `quarantine/legacy_models/baseline_model.pkl` | `44ff8605fd39c38f701235fb07f38357b890baa81d3216b45f2103eae65eaaa8` | 766,743 B | `45cd94b` |
| `feature_scalers.pkl` | `quarantine/legacy_models/feature_scalers.pkl` | `f8addface825dcc9ea7d241ee68d578ac661640718c32c606fcdd326e8edfaea` | 536 B | `45cd94b` |
| `longitudinal_lstm.pt` | `quarantine/legacy_models/longitudinal_lstm.pt` | `4ff257b350392cfb1ff638f8fe8704d3c98f77469647cc1770f3191e2d2f6a9f` | 179,918 B | `45cd94b` |

---

## 3. Replacement Plan
These artifacts have been permanently removed from the application runtime path.
Valid models are introduced in:
- **Phase 2:** Classical baselines (prevalence, single-threshold, velocity, regularized Cox/discrete-time hazard, gradient boosting) and K3 Bayesian joint longitudinal–survival model.
- **Phase 3:** Forward-only state-space and causal sequence models exported to ONNX / safetensors, adhering to strict clinical event horizons without data leakage.
