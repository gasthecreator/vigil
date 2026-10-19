"""ONNX execution wrapper for explicitly supplied research artifacts.

This wrapper does not train, calibrate, validate, or promote a model. It refuses
to invent a fallback model or an uncertainty estimate when those inputs are
missing. The conformal controller abstains until a calibration cohort is fitted.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import onnxruntime as ort

from vigil_ml.conformal_k8 import ConformalPredictionResult, ConformalRiskControllerK8


class VigilProductionRuntime:
    """Run an explicitly supplied ONNX artifact on CPU.

    The historical class name is retained for API compatibility; this class is
    a research wrapper and does not imply production validation.
    """

    def __init__(self, onnx_model_path: Optional[Path] = None):
        if onnx_model_path is None:
            raise ValueError("An explicit ONNX artifact path is required; no fallback model is available")
        if not onnx_model_path.is_file():
            raise FileNotFoundError(f"ONNX artifact does not exist: {onnx_model_path}")
        self.model_path = onnx_model_path

        # Optimized session options
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.session = ort.InferenceSession(str(self.model_path), sess_options=opts, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        input_shape = self.session.get_inputs()[0].shape
        if not input_shape or not isinstance(input_shape[-1], int) or input_shape[-1] <= 0:
            raise ValueError("ONNX artifact must declare a fixed positive feature dimension")
        self.input_dimension = input_shape[-1]
        self.conformal = ConformalRiskControllerK8(alpha_conf=0.10)

    def predict_single_patient(
        self, features: np.ndarray, *, epistemic_std: float
    ) -> ConformalPredictionResult:
        """
        Runs single-patient inference on CPU.
        """
        features = np.asarray(features, dtype=np.float32)
        if features.shape != (self.input_dimension,):
            raise ValueError(f"features must have shape ({self.input_dimension},)")
        if not np.isfinite(features).all():
            raise ValueError("features must contain only finite values")
        x = features.reshape(1, -1)
        raw_prob = float(self.session.run(None, {self.input_name: x})[0][0, 0])
        return self.conformal.predict(raw_prob, epistemic_std, features)

    def benchmark_latency(self, n_calls: int = 1000) -> Dict[str, float]:
        """
        Measures ONNX CPU execution latency over at least 1,000 calls.

        This excludes feature construction, uncertainty estimation, calibration,
        and API overhead. It is a runtime-mechanics measurement only.
        """
        if n_calls < 1000:
            raise ValueError("n_calls must be at least 1000")
        dummy_x = np.zeros(self.input_dimension, dtype=np.float32)
        model_input = dummy_x.reshape(1, -1)
        # Warmup
        for _ in range(50):
            self.session.run(None, {self.input_name: model_input})

        latencies = []
        for _ in range(n_calls):
            t0 = time.perf_counter()
            self.session.run(None, {self.input_name: model_input})
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)  # ms

        latencies = np.array(latencies)
        p50 = float(np.percentile(latencies, 50))
        p95 = float(np.percentile(latencies, 95))
        p99 = float(np.percentile(latencies, 99))

        return {
            "n_calls": n_calls,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "budget_passed": bool(p95 < 100.0),
        }
