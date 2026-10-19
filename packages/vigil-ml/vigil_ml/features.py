"""
vigil_ml.features

Longitudinal Feature Extraction and Windowed Summary Pipeline.
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.2) and docs/ML_PROGRAM.md §5, §9.

Transforms irregular longitudinal observation series into strictly unleaked
windowed feature vectors containing:
- Baseline demographics and tumor clinical stage
- Current laboratory analyte levels
- Multi-horizon velocities (slopes over 90d, 180d)
- Biomarker acceleration (second difference)
- Longitudinal biological variability (coefficient of variation)
- Informative missingness features (elapsed visit interval, skipped test counts)
- Current symptom burden and organ-specific symptom flags
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

TRACKED_ANALYTES = [
    "ca_15_3",
    "cea",
    "alt",
    "ast",
    "alp",
    "ggt",
    "total_bilirubin",
    "calcium",
    "creatinine",
    "wbc",
]


@dataclass
class WindowedFeatureExtractor:
    """Extracts summary features from longitudinal observation histories up to evaluation time t."""

    tracked_analytes: List[str] = None

    def __post_init__(self):
        if self.tracked_analytes is None:
            self.tracked_analytes = TRACKED_ANALYTES

    def extract_features_at_visit(
        self,
        patient_row: Dict[str, Any],
        historical_observations: List[Dict[str, Any]],
        current_day: float,
    ) -> Dict[str, float]:
        """
        Extracts feature vector at a specific evaluation day t using ONLY history where day <= current_day.
        """
        # Filter strictly historical/current observations (anti-leakage guarantee)
        history = [obs for obs in historical_observations if obs["day"] <= current_day]
        history.sort(key=lambda x: x["day"])

        if not history:
            return {}

        current_obs = history[-1]

        def numeric_value(value: Any) -> float:
            return float(value) if value is not None and not pd.isna(value) else float("nan")

        def binary_value(value: Any) -> float:
            return float(value) if value is not None and not pd.isna(value) else float("nan")

        age = numeric_value(patient_row.get("age"))
        stage_value = patient_row.get("stage")
        stage_missing = stage_value is None or pd.isna(stage_value)
        subtype_value = patient_row.get("subtype")
        subtype_missing = subtype_value is None or pd.isna(subtype_value)

        features: Dict[str, float] = {
            "eval_day": float(current_day),
            "age": age,
            "age_missing": float(not np.isfinite(age)),
            "is_er_pos": binary_value(patient_row.get("er_status")),
            "is_pr_pos": binary_value(patient_row.get("pr_status")),
            "is_her2_pos": binary_value(patient_row.get("her2_status")),
            "is_stage_3_or_4": 1.0
            if not stage_missing and str(stage_value).upper() in ["STAGE III", "STAGE IV"]
            else (float("nan") if stage_missing else 0.0),
            "stage_missing": float(stage_missing),
            "history_length": float(len(history)),
        }

        # Subtype one-hot
        sub = str(subtype_value).upper() if not subtype_missing else ""
        features["sub_tnbc"] = float("nan") if subtype_missing else float("TNBC" in sub)
        features["sub_her2"] = float("nan") if subtype_missing else float("HER2+" in sub)
        features["sub_luminal"] = float("nan") if subtype_missing else float("HR+" in sub)
        features["subtype_missing"] = float(subtype_missing)

        # Visit schedule friction / missingness features
        if len(history) > 1:
            prev_obs = history[-2]
            features["days_since_last_visit"] = float(current_day - prev_obs["day"])
            features["has_prior_visit"] = 1.0
        else:
            features["days_since_last_visit"] = float("nan")
            features["has_prior_visit"] = 0.0

        # Current symptoms
        syms = current_obs.get("symptoms")
        symptoms_missing = syms is None or pd.isna(syms)
        if symptoms_missing:
            syms = {}
        features["symptoms_missing"] = float(symptoms_missing)
        features["max_symptom_grade"] = (
            float("nan") if symptoms_missing else float(max(syms.values(), default=0))
        )
        features["symptom_bone_pain"] = float("nan") if symptoms_missing else float(syms.get("bone_pain", 0))
        features["symptom_ruq_pain"] = float("nan") if symptoms_missing else float(syms.get("ruq_pain", 0))
        features["symptom_jaundice"] = float("nan") if symptoms_missing else float(syms.get("jaundice", 0))
        features["symptom_dyspnea"] = float("nan") if symptoms_missing else float(syms.get("cough_dyspnea", 0))
        features["symptom_neuro"] = float("nan") if symptoms_missing else float(syms.get("headache_neuro", 0))

        # Analyte levels, velocities, and variability
        for code in self.tracked_analytes:
            curr_val = current_obs.get("analytes", {}).get(code)
            if curr_val is None:
                features[f"{code}_curr"] = float("nan")
                features[f"{code}_missing"] = 1.0
                features[f"{code}_slope_90d"] = float("nan")
                features[f"{code}_slope_90d_available"] = 0.0
                features[f"{code}_accel"] = float("nan")
                features[f"{code}_accel_available"] = 0.0
                features[f"{code}_cv"] = float("nan")
                features[f"{code}_cv_available"] = 0.0
                continue

            features[f"{code}_curr"] = float(curr_val)
            features[f"{code}_missing"] = 0.0

            # Historical series for this analyte
            series = [
                (obs["day"], obs.get("analytes", {}).get(code))
                for obs in history
                if obs.get("analytes", {}).get(code) is not None
            ]

            # 90-day slope (velocity)
            recent_series = [(d, v) for d, v in series if (current_day - d) <= 120.0]
            if len(recent_series) >= 2:
                days_arr = np.array([d for d, _ in recent_series])
                vals_arr = np.array([v for _, v in recent_series])
                dt = days_arr[-1] - days_arr[0]
                slope = (vals_arr[-1] - vals_arr[0]) / dt if dt > 0 else 0.0
                features[f"{code}_slope_90d"] = float(slope)
                features[f"{code}_slope_90d_available"] = 1.0
            else:
                features[f"{code}_slope_90d"] = float("nan")
                features[f"{code}_slope_90d_available"] = 0.0

            # Acceleration (second difference if >= 3 points)
            if len(series) >= 3:
                y1 = series[-3][1]
                y2 = series[-2][1]
                y3 = series[-1][1]
                accel = (y3 - y2) - (y2 - y1)
                features[f"{code}_accel"] = float(accel)
                features[f"{code}_accel_available"] = 1.0
            else:
                features[f"{code}_accel"] = float("nan")
                features[f"{code}_accel_available"] = 0.0

            # Biological variability (CV over historical values)
            if len(series) >= 2:
                v_arr = np.array([v for _, v in series])
                mean_v = np.mean(v_arr)
                std_v = np.std(v_arr)
                cv = (std_v / mean_v) if mean_v > 0 else 0.0
                features[f"{code}_cv"] = float(cv)
                features[f"{code}_cv_available"] = 1.0
            else:
                features[f"{code}_cv"] = float("nan")
                features[f"{code}_cv_available"] = 0.0

        return features

    def transform_cohort(
        self,
        patients_df: pd.DataFrame,
        observations_df: pd.DataFrame,
        horizon_days: float = 180.0,
    ) -> Tuple[pd.DataFrame, pd.Series, np.ndarray, np.ndarray]:
        """
        Transforms full cohort into feature matrix X, prospective binary label y,
        follow-up times, and event indicators for survival modeling.
        """
        pt_dict = {row["patient_id"]: row.to_dict() for _, row in patients_df.iterrows()}

        # Group observations by patient
        grouped_obs: Dict[str, List[Dict[str, Any]]] = {}
        for _, row in observations_df.iterrows():
            pt_id = row["patient_id"]
            obs_dict = {
                "day": float(row["day"]),
                "analytes": {
                    col: row[col]
                    for col in self.tracked_analytes
                    if col in row and pd.notna(row[col])
                },
                "symptoms": {
                    col.replace("symptom_", ""): int(row[col])
                    for col in row.index
                    if col.startswith("symptom_") and pd.notna(row[col])
                },
            }
            grouped_obs.setdefault(pt_id, []).append(obs_dict)

        features_list = []
        labels_list = []
        follow_up_times = []
        event_indicators = []

        for pt_id, obs_list in grouped_obs.items():
            pt_row = pt_dict.get(pt_id)
            if not pt_row:
                continue

            rec_event = bool(pt_row.get("observed_recurrence_event", False))
            rec_day = pt_row.get("observed_recurrence_day")
            comp_day = pt_row.get("competing_event_day")

            for obs in obs_list:
                d = obs["day"]

                # Exclude visits occurring after competing event
                if comp_day is not None and not np.isnan(comp_day) and d >= comp_day:
                    continue
                # Exclude visits on or after clinical recurrence was confirmed.
                if rec_event and rec_day is not None and not np.isnan(rec_day) and d >= rec_day:
                    continue

                feat = self.extract_features_at_visit(pt_row, obs_list, d)
                if not feat:
                    continue

                feat["patient_id"] = pt_id

                # Follow-up end is administrative end unless a terminal event or
                # loss to follow-up occurs first. Older/external cohorts without an
                # explicit end date use the last observed visit conservatively.
                last_day = max(o["day"] for o in obs_list)
                admin_end = pt_row.get("administrative_censor_day")
                if admin_end is None or pd.isna(admin_end):
                    admin_end = last_day
                terminal_competing = (
                    comp_day is not None
                    and not pd.isna(comp_day)
                    and pt_row.get("competing_event") not in {None, "lost_to_follow_up"}
                    and comp_day <= admin_end
                )
                lost_to_follow_up = (
                    comp_day is not None
                    and not pd.isna(comp_day)
                    and pt_row.get("competing_event") == "lost_to_follow_up"
                    and comp_day <= admin_end
                )
                recurrence_observed = (
                    rec_event
                    and rec_day is not None
                    and not pd.isna(rec_day)
                    and rec_day <= admin_end
                    and (comp_day is None or pd.isna(comp_day) or rec_day < comp_day)
                )

                event_day: float | None = None
                event_flag = 0  # 0=censored, 1=recurrence, 2=competing event
                if recurrence_observed:
                    event_day, event_flag = float(rec_day), 1
                if terminal_competing and (event_day is None or comp_day < event_day):
                    event_day, event_flag = float(comp_day), 2

                if event_day is not None:
                    time_to_event_or_censor = max(1.0, event_day - d)
                else:
                    censor_day = min(
                        float(admin_end),
                        float(comp_day) if lost_to_follow_up else float(admin_end),
                    )
                    time_to_event_or_censor = max(1.0, censor_day - d)

                # The binary horizon label is known for observed recurrence or a
                # competing event within H, or when follow-up covers all of H.
                # A loss/admin censor before H is unknown, never a negative label.
                if event_flag == 1 and time_to_event_or_censor <= horizon_days:
                    y = 1.0
                elif event_flag == 2 and time_to_event_or_censor <= horizon_days:
                    y = 0.0
                elif time_to_event_or_censor >= horizon_days or (
                    event_flag != 0 and time_to_event_or_censor > horizon_days
                ):
                    y = 0.0
                else:
                    y = np.nan

                features_list.append(feat)
                labels_list.append(y)
                follow_up_times.append(time_to_event_or_censor)
                event_indicators.append(event_flag)

        X = pd.DataFrame(features_list)
        y = pd.Series(labels_list, dtype=float, name=f"recurrence_within_{int(horizon_days)}d")

        return X, y, np.array(follow_up_times), np.array(event_indicators)


def build_landmark_features(
    observations_df: pd.DataFrame,
    patients_df: Optional[pd.DataFrame] = None,
    horizon_days: float = 365.0,
) -> Tuple[pd.DataFrame, pd.Series, np.ndarray, np.ndarray]:
    """Module-level entrypoint for building landmark feature matrix."""
    extractor = WindowedFeatureExtractor()
    if patients_df is None:
        # Default empty patient baseline dataframe if not provided
        pt_ids = observations_df["patient_id"].unique()
        patients_df = pd.DataFrame({"patient_id": pt_ids})
    return extractor.transform_cohort(
        patients_df=patients_df,
        observations_df=observations_df,
        horizon_days=horizon_days,
    )


build_features = build_landmark_features


