"""Inference Engine for Vigil Oncology Surveillance Platform.

Per MASTER_PLAN.md §14 WP0.3 and ADR-0002:
- Prototype models (A1 circular labels, A2 invalid metrics, A3 acausal BiLSTM,
  A8 pickled artifacts) are permanently QUARANTINED.
- Zero pickle.load calls in the default runtime execution path.
- Baseline organ susceptibility uses literature/SEER Bayesian priors (EVIDENCE E12).
- Longitudinal surveillance uses deterministic biomarker velocity rules with
  synthetic-data indicators until Phase 2 and Phase 3 models are validated.
"""

from typing import Any
import numpy as np

from vigil_api.config import settings


class VigilEngine:
    """Unified inference engine for multimodal oncology surveillance.

    Thread-safe and optimized for FastAPI integration.
    Operates in quarantined research mode with zero unverified pickled models.
    """

    _instance = None

    def __init__(self, artifacts_dir: str | None = None):
        self.artifacts_dir = artifacts_dir
        self.is_loaded = True
        self.is_quarantined = True
        self.model_version = "0.1.0-alpha-quarantined"
        self.status = "quarantined_pending_phase_3"

    @classmethod
    def get_instance(cls, artifacts_dir: str | None = None) -> "VigilEngine":
        if cls._instance is None:
            cls._instance = cls(artifacts_dir=artifacts_dir)
        return cls._instance

    def predict_baseline_susceptibility(self, patient_data: dict[str, Any]) -> dict[str, float]:
        """Model A inference: Maps baseline patient pathology to organ susceptibility vector.

        Uses literature/SEER-calibrated priors (EVIDENCE E12) rather than the circular
        generator vector from the prototype.
        """
        er = bool(patient_data.get("er_status", True))
        pr = bool(patient_data.get("pr_status", True))
        her2 = bool(patient_data.get("her2_status", False))
        stage = int(patient_data.get("tumor_stage", 2))

        # Base prior from SEER distant metastasis distributions (E12):
        # Bone predominance in HR+/HER2- disease; visceral/brain shifts in HER2+ and TNBC.
        if er and pr and not her2:
            # HR+/HER2- luminal subtype: high bone tropism
            base = {"bone": 0.52, "liver": 0.22, "lung": 0.18, "brain": 0.08}
        elif her2:
            # HER2+ subtype: higher liver and brain predilection
            base = {"bone": 0.32, "liver": 0.34, "lung": 0.20, "brain": 0.14}
        elif not er and not pr and not her2:
            # Triple-negative breast cancer (TNBC): visceral and CNS predilection
            base = {"bone": 0.28, "liver": 0.32, "lung": 0.24, "brain": 0.16}
        else:
            base = {"bone": 0.40, "liver": 0.30, "lung": 0.20, "brain": 0.10}

        # Stage adjustments (higher stage slightly widens systemic distribution)
        if stage >= 3:
            base["liver"] += 0.03
            base["brain"] += 0.02

        # Normalize to ensure sum is strictly 1.0
        total = sum(base.values())
        return {
            "bone": float(round(base["bone"] / total, 4)),
            "liver": float(round(base["liver"] / total, 4)),
            "lung": float(round(base["lung"] / total, 4)),
            "brain": float(round(base["brain"] / total, 4)),
        }

    def predict_risk(
        self,
        patient_id: str,
        new_lab_result: dict[str, Any],
        historical_labs: list[dict[str, Any]] | None = None,
        baseline_profile: dict[str, Any] | None = None,
    ) -> tuple[float, bool, str]:
        """Calculates metastasis risk signal, triage flag, and justification text.

        Uses transparent biomarker velocity tracking and literature physiological cutoffs.
        Returns:
            (calculated_metastasis_risk, triage_flag, justification_text)
        """
        organ_vec = {"bone": 0.40, "liver": 0.30, "lung": 0.20, "brain": 0.10}
        if baseline_profile and "target_organ_susceptibility_vector" in baseline_profile:
            organ_vec = baseline_profile["target_organ_susceptibility_vector"]

        ca153 = float(new_lab_result.get("ca_15_3", 18.0))
        alt = float(new_lab_result.get("alt_level", 20.0))
        ast = float(new_lab_result.get("ast_level", 20.0))
        cr = float(new_lab_result.get("creatinine", 0.9))
        wbc = float(new_lab_result.get("wbc_count", 6.5))

        # Velocity calculation from historical sequence
        ca_velocity_pct = 0.0
        alt_velocity_pct = 0.0
        if historical_labs:
            sorted_hist = sorted(historical_labs, key=lambda x: str(x.get("date_drawn", "")))
            last_lab = sorted_hist[-1]
            prev_ca = float(last_lab.get("ca_15_3", 18.0))
            prev_alt = float(last_lab.get("alt_level", 20.0))
            if prev_ca > 0:
                ca_velocity_pct = ((ca153 - prev_ca) / prev_ca) * 100.0
            if prev_alt > 0:
                alt_velocity_pct = ((alt - prev_alt) / prev_alt) * 100.0

        # Heuristic risk index based on established physiological bounds (E1, E2)
        risk_components = []
        # CA 15-3 normal upper bound ~30 U/mL (E1)
        if ca153 > 30.0:
            risk_components.append(min((ca153 - 30.0) / 40.0, 0.45))
        if ca_velocity_pct > 25.0:
            risk_components.append(min(ca_velocity_pct / 100.0 * 0.30, 0.35))
        # ALT/AST hepatic transaminitis (>45 U/L)
        if alt > 45.0 or ast > 45.0:
            risk_components.append(min((max(alt, ast) - 45.0) / 50.0 * 0.25, 0.30))
        if alt_velocity_pct > 40.0:
            risk_components.append(0.15)
        # Leukocytosis
        if wbc > 10.5:
            risk_components.append(0.10)

        raw_score = sum(risk_components) if risk_components else 0.12
        risk_score = float(np.clip(raw_score, 0.05, 0.95))
        risk_score = float(round(risk_score, 4))

        triage_flag = bool(risk_score >= settings.CLINICAL_ALERT_THRESHOLD)

        justification_text = self._synthesize_justification(
            risk_score=risk_score,
            new_lab=new_lab_result,
            ca_velocity_pct=ca_velocity_pct,
            alt_velocity_pct=alt_velocity_pct,
            organ_vec=organ_vec,
        )

        return risk_score, triage_flag, justification_text

    def _synthesize_justification(
        self,
        risk_score: float,
        new_lab: dict[str, Any],
        ca_velocity_pct: float,
        alt_velocity_pct: float,
        organ_vec: dict[str, float],
    ) -> str:
        """Synthesizes factual, provenance-bound justification with clinical disclaimer."""
        ca153 = float(new_lab.get("ca_15_3", 18.0))
        alt = float(new_lab.get("alt_level", 20.0))
        ast = float(new_lab.get("ast_level", 20.0))
        wbc = float(new_lab.get("wbc_count", 6.5))

        top_organ = max(organ_vec.items(), key=lambda kv: kv[1])[0].capitalize()
        top_organ_score = round(organ_vec.get(top_organ.lower(), 0.25) * 100, 1)

        drivers = []
        if ca_velocity_pct > 25.0 or ca153 > 30.0:
            drivers.append(f"CA 15-3 surge ({ca153} U/mL, +{ca_velocity_pct:.1f}%)")
        if alt > 45.0 or ast > 45.0 or alt_velocity_pct > 40.0:
            drivers.append(f"transaminitis (ALT {alt} U/L, AST {ast} U/L)")
        if wbc > 10.5:
            drivers.append(f"reactive leukocytosis ({wbc} x10^9/L)")

        driver_str = "; ".join(drivers) if drivers else "stable physiological variance"

        disclaimer_prefix = "[SYNTHETIC RESEARCH PROTOTYPE — NOT A DIAGNOSIS] "

        if risk_score >= settings.CLINICAL_ALERT_THRESHOLD:
            return (
                f"{disclaimer_prefix}ACTIONABLE ALERT (Estimated Risk Signal: {risk_score:.2f}): "
                f"Longitudinal biomarker trajectory shows critical divergence ({driver_str}), "
                f"aligned with baseline {top_organ} susceptibility ({top_organ_score}%). "
                f"Prompt clinician review and confirmatory restaging recommended per institution protocol."
            )
        elif risk_score >= 0.40:
            return (
                f"{disclaimer_prefix}ELEVATED SURVEILLANCE WATCH (Estimated Risk Signal: {risk_score:.2f}): "
                f"Upward drift detected ({driver_str}) in patient with elevated {top_organ} "
                f"susceptibility ({top_organ_score}%). Recommend repeat draw at shortened interval."
            )
        else:
            return (
                f"{disclaimer_prefix}STABLE SURVEILLANCE (Estimated Risk Signal: {risk_score:.2f}): "
                f"Serial biomarkers remain within expected physiological bounds. Continue routine follow-up."
            )


# Backwards compatibility alias for legacy prototype references
SentinelEngine = VigilEngine
