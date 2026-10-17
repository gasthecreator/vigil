# Vigil Machine Learning Compute & Hardware Plan

## 1. Hardware Profile & Execution Targets
Vigil is designed and optimized for dual execution profiles:
1. **Developer Workstation / Edge Runtime (Default):**
   - **Target Architecture:** Apple Silicon (M-series, MPS backend) and standard x86_64 / arm64 CPU.
   - **Memory Envelope:** 16 GB unified RAM; maximum training memory footprint $\le 4\text{ GB}$.
   - **Concurrency:** Multi-process CPU data loading with vectorized PyTorch batching.
   - **Inference Latency Budget:** $p95 < 100\text{ ms}$ on single-core CPU for production sequential filtering and ONNX runtime inference.

2. **Cloud Batch Training & Grid Search (Scalable Profile):**
   - **Target Accelerator:** NVIDIA A10G / T4 / L4 (CUDA backend).
   - **Container Specification:** `ghcr.io/gasthecreator/vigil-ml:latest` built on `python:3.12-slim` with PyTorch.
   - **Pre-emption & Checkpointing:** Fault-tolerant state-dict saving via Safetensors after every training epoch.

## 2. Device Abstraction Architecture
All deep learning and state-space models in `vigil-ml` utilize an explicit device resolver:
```python
import torch


def resolve_device(preferred: str | None = None) -> torch.device:
    if preferred:
        return torch.device(preferred)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
```

## 3. Training Budgets & Model Dimensionality

| Family | Model ID | Parameter Scale | Memory Budget | Max Training Time (CPU/MPS) | Latency Target (p95) |
|---|---|---|---|---|---|
| **K1** Kinetic SDE/ODE | `K1_KINETIC` | ~45,000 | < 250 MB | < 60s per cohort | < 80 ms |
| **K2** Sequential e-Process | `K2_SEQUENTIAL` | ~5,000 | < 50 MB | < 15s per cohort | < 5 ms |
| **K3** Bayesian Joint Model | `K3_JOINT_MODEL` | ~12,000 | < 150 MB | < 30s per cohort | < 10 ms |
| **K4** Deep Zoo (GRU-D, Neural CDE, etc.) | `K4_DEEP_ZOO` | ~85,000 | < 400 MB | < 90s per cohort | < 45 ms |
| **K5** Hierarchical Lab Harmonisation | `K5_HARMONISATION` | ~8,000 | < 80 MB | < 20s per cohort | < 15 ms |
| **K6** Active Sensing Policy | `K6_ACTIVE_SENSING`| ~10,000 | < 100 MB | < 30s per cohort | < 25 ms |
| **K8** Production Ensemble + OOD | `K8_ENSEMBLE` | ~160,000 | < 600 MB | < 120s full pipeline | < 95 ms |

## 4. Reproducibility & Determinism
All training and evaluation pipelines enforce deterministic random state:
- Python standard library `random.seed(seed)`
- NumPy `np.random.default_rng(seed)`
- PyTorch `torch.manual_seed(seed)`, `torch.use_deterministic_algorithms(True, warn_only=True)`
- Global seeds are recorded in all `results.json` run outputs.
