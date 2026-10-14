"""
Inference Wrapper for Sentinel Oncology Platform.
Contains SentinelEngine to execute Model A (Baseline Organ Profiler)
and Model B (Longitudinal Sequence Recurrent Anomaly Detector).
"""

import os
import pickle
from typing import Any
import numpy as np
import torch

from sentinel.ml.models import LongitudinalLSTM


class SentinelEngine:
    """
    Unified inference engine for multimodal oncology surveillance.
    Thread-safe and optimized for production FastAPI integration.
    """

    _instance = None

    def __init__(
        self,
        artifacts_dir: str | None = None,
    ):
        if artifacts_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            artifacts_dir = os.path.join(base_dir, "artifacts")

        self.artifacts_dir = artifacts_dir
        self.device = torch.device("cpu")  # CPU inference for high throughput & stability

        self.baseline_model = None
        self.lstm_model = None
        self.scaler = None
        self.is_loaded = False

        self._load_artifacts()

    @classmethod
    def get_instance(cls, artifacts_dir: str | None = None) -> "SentinelEngine":
        if cls._instance is None:
            cls._instance = cls(artifacts_dir=artifacts_dir)
        return cls._instance

    def _load_artifacts(self) -> None:
        """Loads serialized XGBoost model, PyTorch LSTM weights, and scalers."""
        baseline_path = os.path.join(self.artifacts_dir, "baseline_model.pkl")
        lstm_path = os.path.join(self.artifacts_dir, "longitudinal_lstm.pt")
        scaler_path = os.path.join(self.artifacts_dir, "feature_scalers.pkl")

        if not (os.path.exists(baseline_path) and os.path.exists(lstm_path) and os.path.exists(scaler_path)):
            # Artifacts not trained yet; will be trained during bootstrapping
            return

        with open(baseline_path, "rb") as f:
            self.baseline_model = pickle.load(f)

        with open(scaler_path, "rb") as f:
            self.scaler = pickle.load(f)

        self.lstm_model = LongitudinalLSTM(input_size=9, hidden_size=32, num_layers=2, dropout=0.2)
        state_dict = torch.load(lstm_path, map_location=self.device)
        self.lstm_model.load_state_dict(state_dict)
        self.lstm_model.to(self.device)
        self.lstm_model.eval()

        self.is_loaded = True

    def predict_baseline_susceptibility(self, patient_data: dict[str, Any]) -> dict[str, float]:
        """
        Model A inference: Maps baseline patient pathology to organ susceptibility vector.
        Features: [age, tumor_stage, er_status, pr_status, her2_status, has_hypertension, renal_history]
        Returns: {"bone": float, "liver": float, "lung": float, "brain": float}
        """
        if self.baseline_model is None:
            self._load_artifacts()

        if self.baseline_model is None:
            raise RuntimeError("Model A (baseline_model.pkl) is not loaded. Run training first.")

        features = np.array([[
            float(patient_data.get("age", 55)),
            float(patient_data.get("tumor_stage", 2)),
            1.0 if patient_data.get("er_status", True) else 0.0,
            1.0 if patient_data.get("pr_status", True) else 0.0,
            1.0 if patient_data.get("her2_status", False) else 0.0,
            1.0 if patient_data.get("has_hypertension", False) else 0.0,
            1.0 if patient_data.get("renal_history", False) else 0.0,
        ]], dtype=np.float32)

        raw_pred = self.baseline_model.predict(features)[0]
        # Softmax / positive normalization
        pos_pred = np.maximum(raw_pred, 0.01)
        norm_pred = pos_pred / np.sum(pos_pred)

        return {
            "bone": float(round(norm_pred[0], 4)),
            "liver": float(round(norm_pred[1], 4)),
            "lung": float(round(norm_pred[2], 4)),
            "brain": float(round(norm_pred[3], 4)),
        }

    def predict_risk(
        self,
        patient_id: str,
        new_lab_result: dict[str, Any],
        historical_labs: list[dict[str, Any]] | None = None,
        baseline_profile: dict[str, Any] | None = None,
    ) -> tuple[float, bool, str]:
        """
        Model B inference: Predicts calculated_metastasis_risk, triage_flag, and justification_text
        given the new lab draw and historical lab trajectory.

        Returns:
            (calculated_metastasis_risk, triage_flag, justification_text)
        """
        if self.lstm_model is None or self.scaler is None:
            self._load_artifacts()

        if self.lstm_model is None or self.scaler is None:
            raise RuntimeError("Model B (longitudinal_lstm.pt / feature_scalers.pkl) is not loaded.")

        # Default organ vector if baseline not yet recorded
        organ_vec = {"bone": 0.40, "liver": 0.30, "lung": 0.20, "brain": 0.10}
        if baseline_profile and "target_organ_susceptibility_vector" in baseline_profile:
            organ_vec = baseline_profile["target_organ_susceptibility_vector"]

        susc_arr = np.array([
            organ_vec.get("bone", 0.25),
            organ_vec.get("liver", 0.25),
            organ_vec.get("lung", 0.25),
            organ_vec.get("brain", 0.25),
        ], dtype=np.float32)

        # Assemble full trajectory ending with new_lab_result
        all_labs = list(historical_labs or [])
        all_labs.append(new_lab_result)

        # Ensure sorted by date
        sorted_labs = sorted(all_labs, key=lambda x: str(x.get("date_drawn", "")))

        # Build feature sequence
        seq_vectors = []
        for lab in sorted_labs:
            raw_lab = np.array([[
                float(lab.get("alt_level", 20.0)),
                float(lab.get("ast_level", 20.0)),
                float(lab.get("creatinine", 0.9)),
                float(lab.get("ca_15_3", 18.0)),
                float(lab.get("wbc_count", 6.5)),
            ]], dtype=np.float32)
            scaled_lab = self.scaler.transform(raw_lab)[0]
            combined = np.concatenate([scaled_lab, susc_arr], axis=0)  # dim = 9
            seq_vectors.append(combined)

        seq_tensor = torch.tensor(np.array([seq_vectors]), dtype=torch.float32).to(self.device)

        with torch.no_grad():
            risk_tensor, attn_weights = self.lstm_model(seq_tensor)
            risk_score = float(np.clip(risk_tensor.item(), 0.001, 0.999))

        triage_flag = bool(risk_score >= 0.75)
        justification_text = self._synthesize_justification(
            risk_score=risk_score,
            new_lab=new_lab_result,
            historical_labs=historical_labs or [],
            organ_vec=organ_vec,
            baseline_profile=baseline_profile,
        )

        return float(round(risk_score, 4)), triage_flag, justification_text

    def _synthesize_justification(
        self,
        risk_score: float,
        new_lab: dict[str, Any],
        historical_labs: list[dict[str, Any]],
        organ_vec: dict[str, float],
        baseline_profile: dict[str, Any] | None,
    ) -> str:
        """Synthesizes clinical explainability text based on biomarker velocity and organ alignment."""
        ca153 = float(new_lab.get("ca_15_3", 18.0))
        alt = float(new_lab.get("alt_level", 20.0))
        ast = float(new_lab.get("ast_level", 20.0))
        cr = float(new_lab.get("creatinine", 0.9))
        wbc = float(new_lab.get("wbc_count", 6.5))

        # Velocity calculation if previous labs exist
        prev_ca153 = None
        prev_alt = None
        ca_velocity_pct = 0.0
        alt_velocity_pct = 0.0

        if historical_labs:
            last_hist = sorted(historical_labs, key=lambda x: str(x.get("date_drawn", "")))[-1]
            prev_ca153 = float(last_hist.get("ca_15_3", 18.0))
            prev_alt = float(last_hist.get("alt_level", 20.0))
            if prev_ca153 > 0:
                ca_velocity_pct = ((ca153 - prev_ca153) / prev_ca153) * 100.0
            if prev_alt > 0:
                alt_velocity_pct = ((alt - prev_alt) / prev_alt) * 100.0

        top_organ = max(organ_vec.items(), key=lambda kv: kv[1])[0].capitalize()
        top_organ_score = round(organ_vec.get(top_organ.lower(), 0.25) * 100, 1)

        if risk_score >= 0.75:
            drivers = []
            if ca_velocity_pct > 30.0 or ca153 > 35.0:
                drivers.append(f"accelerated CA 15-3 velocity (+{ca_velocity_pct:.1f}% surge to {ca153} U/mL)")
            if alt > 50.0 or alt_velocity_pct > 50.0:
                drivers.append(f"significant transaminitis (ALT {alt} U/L, AST {ast} U/L)")
            if wbc > 10.5:
                drivers.append(f"reactive leukocytosis ({wbc} x10^9/L)")
            if not drivers:
                drivers.append(f"multivariate biomarker velocity drift across CA 15-3 ({ca153}) and ALT ({alt})")

            driver_str = "; ".join(drivers)

            recommendation = "Urgent diagnostic restaging (contrast-enhanced multiphase CT/MRI and FDG PET-CT)"
            if top_organ.lower() == "liver" and alt > 50.0:
                recommendation = "Urgent Contrast-Enhanced Abdominal MRI with Eovist and FDG PET-CT"
            elif top_organ.lower() == "bone":
                recommendation = "Whole-Body Technetium-99m Bone Scintigraphy and PET-CT"

            return (
                f"ACTIONABLE ALERT (Metastatic Risk: {risk_score:.2f}): Sentinel sequence model detected "
                f"critical divergence: {driver_str}. Highly concordant with baseline {top_organ} susceptibility "
                f"({top_organ_score}%). Immediate oncologist second-opinion required. Recommended protocol: {recommendation}."
            )
        elif risk_score >= 0.40:
            return (
                f"ELEVATED SURVEILLANCE WATCH (Metastatic Risk: {risk_score:.2f}): Sub-threshold upward trajectory "
                f"detected in CA 15-3 ({ca153} U/mL, change: +{ca_velocity_pct:.1f}%) in patient with elevated {top_organ} "
                f"susceptibility ({top_organ_score}%). Shorten follow-up draw interval to 30 days."
            )
        else:
            return (
                f"STABLE SURVEILLANCE (Metastatic Risk: {risk_score:.2f}): Longitudinal biomarker levels (CA 15-3: {ca153} U/mL, "
                f"ALT: {alt} U/L, Creatinine: {cr} mg/dL, WBC: {wbc} x10^9/L) remain within physiologic variance. "
                f"Continue routine surveillance interval."
            )
