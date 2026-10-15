"""
packages/vigil-ml/vigil_ml/export.py

ONNX and Safetensors Export Engine for Vigil Models.
Enforces:
1. Export to ONNX bytecode format.
2. Serialization to Safetensors format (safe binary representation).
3. Numerical parity tests between PyTorch eager execution and ONNX runtime (max diff < 1e-4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np
import onnxruntime as ort
import safetensors.torch
import torch
import torch.nn as nn


class SurrogateInferenceNet(nn.Module):
    """
    Standard production inference surrogate network for Vigil risk prediction.
    Takes 15-dimensional input vector (analytes, velocities, clinical covariates).
    """

    def __init__(self, input_dim: int = 15, hidden_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def export_to_safetensors(model: nn.Module, output_path: Path) -> Path:
    """
    Saves model state dict safely in Safetensors format.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    safetensors.torch.save_model(model, str(output_path))
    return output_path


def export_to_onnx(model: nn.Module, output_path: Path, input_dim: int = 15) -> Path:
    """
    Exports PyTorch model to ONNX runtime format.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    dummy_input = torch.randn(1, input_dim, dtype=torch.float32)

    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        input_names=["input"],
        output_names=["risk_output"],
        dynamic_axes={"input": {0: "batch_size"}, "risk_output": {0: "batch_size"}},
        opset_version=17,
    )
    return output_path


def verify_onnx_parity(
    model: nn.Module, onnx_path: Path, input_dim: int = 15, n_samples: int = 100
) -> Dict[str, Any]:
    """
    Validates numerical parity between PyTorch eager mode and ONNX runtime.
    Tolerance: max absolute error < 1e-4.
    """
    model.eval()
    rng = np.random.default_rng(2026)
    test_x = rng.normal(0, 1.0, (n_samples, input_dim)).astype(np.float32)

    # PyTorch output
    with torch.no_grad():
        pt_out = model(torch.from_numpy(test_x)).numpy()

    # ONNX output
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_inputs = {session.get_inputs()[0].name: test_x}
    ort_out = session.run(None, ort_inputs)[0]

    max_diff = float(np.max(np.abs(pt_out - ort_out)))
    parity_passed = max_diff < 1e-4

    return {
        "n_samples": n_samples,
        "max_absolute_difference": max_diff,
        "parity_passed": parity_passed,
    }
