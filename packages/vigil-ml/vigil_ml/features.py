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
from vigil_core.analytes import ANALYTE_REGISTRY

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

TRACKED_SYMPTOMS = (
    "bone_pain",
    "jaundice",
    "ruq_pain",
    "cough_dyspnea",
    "headache_neuro",
    "fatigue_weight_loss",
)

SUPPORTED_COMPETING_EVENTS = frozenset(
    {
        "cardiovascular_event",
        "death",
        "lost_to_follow_up",
    }
)
THERAPY_HISTORY_COLUMNS = {
    "chemotherapy_given": "history_chemotherapy_given",
    "endocrine_therapy": "history_endocrine_therapy",
    "radiotherapy_given": "history_radiotherapy_given",
}
NO_ACTIVE_TREATMENT = "none"


@dataclass
class WindowedFeatureExtractor:
    """Extracts summary features from longitudinal observation histories up to evaluation time t."""

    tracked_analytes: List[str] = None

    def __post_init__(self):
        if self.tracked_analytes is None:
            self.tracked_analytes = list(TRACKED_ANALYTES)
        else:
            values = list(self.tracked_analytes)
            if any(not isinstance(code, str) for code in values):
                raise ValueError("tracked_analytes must contain only analyte codes")
            if len(values) != len(set(values)):
                raise ValueError("tracked_analytes must not contain duplicates")
            unsupported = set(values) - set(ANALYTE_REGISTRY)
            if unsupported:
                raise ValueError(
                    f"tracked_analytes contains unregistered analytes: {sorted(unsupported)}"
                )
            self.tracked_analytes = values

    @staticmethod
    def _advanced_stage(stage_value: Any) -> float:
        value = str(stage_value).strip().upper()
        if value.startswith("STAGE "):
            value = value[6:]
        stage_groups = {
            "I": "I",
            "IA": "I",
            "IB": "I",
            "II": "II",
            "IIA": "II",
            "IIB": "II",
            "IIC": "II",
            "III": "III",
            "IIIA": "III",
            "IIIB": "III",
            "IIIC": "III",
            "IIID": "III",
            "IV": "IV",
            "IVA": "IV",
            "IVB": "IV",
        }
        if value not in stage_groups:
            raise ValueError(f"unsupported stage value: {stage_value!r}")
        return float(stage_groups[value] in {"III", "IV"})

    @staticmethod
    def _subtype_flags(subtype_value: Any) -> tuple[float, float, float, float]:
        value = str(subtype_value).strip().upper()
        groups = {
            "TNBC": (1.0, 0.0, 0.0),
            "HER2+": (0.0, 1.0, 0.0),
            "HR+": (0.0, 0.0, 1.0),
            "HR+HER2-": (0.0, 0.0, 1.0),
            "HR+/HER2-": (0.0, 0.0, 1.0),
            "UNCLASSIFIED": (0.0, 0.0, 0.0),
        }
        if value not in groups:
            raise ValueError(f"unsupported subtype value: {subtype_value!r}")
        tnbc, her2, luminal = groups[value]
        return tnbc, her2, luminal, float(value == "UNCLASSIFIED")

    def extract_features_at_visit(
        self,
        patient_row: Dict[str, Any],
        historical_observations: List[Dict[str, Any]],
        current_day: float,
        *,
        synthetic_only: bool | None = None,
    ) -> Dict[str, float]:
        """
        Extracts feature vector at a specific evaluation day t using ONLY history where day <= current_day.
        """
        # Validate the complete input before applying the anti-leakage time filter.
        if isinstance(current_day, (bool, np.bool_)):
            raise ValueError("current_day must be numeric, not boolean")
        if not np.isfinite(float(current_day)):
            raise ValueError("current_day must be finite")
        if any(isinstance(obs.get("day"), (bool, np.bool_)) for obs in historical_observations):
            raise ValueError("observation days must be numeric, not boolean")
        try:
            all_days = np.asarray([float(obs["day"]) for obs in historical_observations], dtype=float)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("every observation must have a numeric day") from exc
        if not np.isfinite(all_days).all():
            raise ValueError("observation days must be finite")
        if len(np.unique(all_days)) != len(all_days):
            raise ValueError("each patient must have at most one observation per day")
        history = [obs for obs in historical_observations if float(obs["day"]) <= current_day]
        history.sort(key=lambda x: x["day"])

        if not history:
            return {}

        current_obs = history[-1]

        def numeric_value(value: Any) -> float:
            if value is None or pd.isna(value):
                return float("nan")
            if isinstance(value, (bool, np.bool_)):
                raise ValueError("present numeric patient features must not be boolean")
            result = float(value)
            if not np.isfinite(result):
                raise ValueError("present numeric patient features must be finite")
            return result

        def binary_value(value: Any) -> float:
            if value is None or pd.isna(value):
                return float("nan")
            result = float(value)
            if result not in (0.0, 1.0):
                raise ValueError("present receptor status features must be binary")
            return result

        age = numeric_value(patient_row.get("age"))
        receptor_missing = {
            name: patient_row.get(name) is None or pd.isna(patient_row.get(name))
            for name in ("er_status", "pr_status", "her2_status")
        }
        stage_value = patient_row.get("stage")
        stage_missing = stage_value is None or pd.isna(stage_value)
        subtype_value = patient_row.get("subtype")
        subtype_missing = subtype_value is None or pd.isna(subtype_value)
        advanced_stage = float("nan") if stage_missing else self._advanced_stage(stage_value)

        features: Dict[str, float] = {
            "eval_day": float(current_day),
            "age": age,
            "age_missing": float(not np.isfinite(age)),
            "is_er_pos": binary_value(patient_row.get("er_status")),
            "er_status_missing": float(receptor_missing["er_status"]),
            "is_pr_pos": binary_value(patient_row.get("pr_status")),
            "pr_status_missing": float(receptor_missing["pr_status"]),
            "is_her2_pos": binary_value(patient_row.get("her2_status")),
            "her2_status_missing": float(receptor_missing["her2_status"]),
            "is_stage_3_or_4": advanced_stage,
            "stage_missing": float(stage_missing),
            "history_length": float(len(history)),
        }

        # Keep pre-index therapy history and current active treatment separate.
        # A missing partner field must not be interpreted as "no treatment".
        for source_column, feature_name in THERAPY_HISTORY_COLUMNS.items():
            value = patient_row.get(source_column)
            missing = value is None or (pd.api.types.is_scalar(value) and pd.isna(value))
            if missing:
                features[feature_name] = float("nan")
                features[f"{feature_name}_missing"] = 1.0
            elif isinstance(value, (bool, np.bool_)):
                features[feature_name] = float(value)
                features[f"{feature_name}_missing"] = 0.0
            elif (
                isinstance(value, (int, np.integer, float, np.floating))
                and np.isfinite(value)
                and value in (0, 1)
            ):
                features[feature_name] = float(value)
                features[f"{feature_name}_missing"] = 0.0
            else:
                raise ValueError(f"{source_column} must be a non-null boolean or 0/1")

        treatment_available = current_obs.get(
            "_treatment_status_available", "treatment_active" in current_obs
        )
        treatment_value = current_obs.get("treatment_active")
        if not treatment_available:
            active_treatment = float("nan")
        elif treatment_value is None or (
            pd.api.types.is_scalar(treatment_value) and pd.isna(treatment_value)
        ):
            active_treatment = 0.0 if synthetic_only is True else float("nan")
        elif isinstance(treatment_value, str) and treatment_value.strip():
            # CohortDataset's direct survival-feature API uses this explicit
            # sentinel; unlike null, it is known inactive status.
            active_treatment = float(
                treatment_value.strip().casefold() != NO_ACTIVE_TREATMENT
            )
        else:
            raise ValueError("treatment_active must be a non-empty treatment name or missing")
        features["active_treatment"] = active_treatment
        features["active_treatment_missing"] = float(not np.isfinite(active_treatment))

        # Subtype one-hot
        subtype_flags = (
            (float("nan"), float("nan"), float("nan"), 0.0)
            if subtype_missing
            else self._subtype_flags(subtype_value)
        )
        features["sub_tnbc"], features["sub_her2"], features["sub_luminal"] = subtype_flags[:3]
        features["subtype_missing"] = float(subtype_missing)
        features["subtype_unclassified"] = subtype_flags[3]

        # Visit schedule friction / missingness features
        if len(history) > 1:
            prev_obs = history[-2]
            features["days_since_last_visit"] = float(current_day - prev_obs["day"])
            features["has_prior_visit"] = 1.0
        else:
            features["days_since_last_visit"] = float("nan")
            features["has_prior_visit"] = 0.0

        # Current symptoms
        raw_symptoms = current_obs.get("symptoms")
        if raw_symptoms is None or (
            pd.api.types.is_scalar(raw_symptoms) and pd.isna(raw_symptoms)
        ):
            syms: Dict[str, Any] = {}
        elif isinstance(raw_symptoms, dict):
            syms = raw_symptoms
        else:
            raise ValueError("symptoms must be a mapping or missing")
        if any(not isinstance(name, str) for name in syms):
            raise ValueError("symptom names must be strings")
        unknown_symptoms = set(syms) - set(TRACKED_SYMPTOMS)
        if unknown_symptoms:
            raise ValueError(f"unsupported symptom names: {sorted(unknown_symptoms)}")

        symptom_values: Dict[str, float] = {}
        for name, value in syms.items():
            if value is None or (
                pd.api.types.is_scalar(value) and pd.isna(value)
            ):
                continue
            if isinstance(value, (bool, np.bool_)):
                raise ValueError(f"symptom {name} must be an integer grade, not boolean")
            if not pd.api.types.is_scalar(value):
                raise ValueError(f"symptom {name} must be a scalar grade")
            grade = float(value)
            if not np.isfinite(grade) or grade not in (0.0, 1.0, 2.0, 3.0, 4.0):
                raise ValueError(f"symptom {name} must be a finite grade from 0 to 4")
            symptom_values[name] = grade

        symptom_missing = {
            name: name not in symptom_values for name in TRACKED_SYMPTOMS
        }
        features["symptoms_missing"] = float(any(symptom_missing.values()))
        features["max_symptom_grade"] = (
            float(max(symptom_values[name] for name in TRACKED_SYMPTOMS))
            if not any(symptom_missing.values())
            else float("nan")
        )
        feature_names = {
            "bone_pain": "symptom_bone_pain",
            "ruq_pain": "symptom_ruq_pain",
            "jaundice": "symptom_jaundice",
            "cough_dyspnea": "symptom_dyspnea",
            "headache_neuro": "symptom_neuro",
        }
        for name, feature_name in feature_names.items():
            features[feature_name] = symptom_values.get(name, float("nan"))
            features[f"{feature_name}_missing"] = float(symptom_missing[name])
        features["symptom_fatigue_weight_loss_missing"] = float(
            symptom_missing["fatigue_weight_loss"]
        )

        # Analyte levels, velocities, and variability
        for code in self.tracked_analytes:
            curr_val = current_obs.get("analytes", {}).get(code)
            if curr_val is None or pd.isna(curr_val):
                features[f"{code}_curr"] = float("nan")
                features[f"{code}_missing"] = 1.0
                features[f"{code}_slope_90d"] = float("nan")
                features[f"{code}_slope_90d_available"] = 0.0
                features[f"{code}_accel"] = float("nan")
                features[f"{code}_accel_available"] = 0.0
                features[f"{code}_cv"] = float("nan")
                features[f"{code}_cv_available"] = 0.0
                continue

            if isinstance(curr_val, (bool, np.bool_)):
                raise ValueError(f"{code} measurements must be numeric, not boolean")
            curr_val = float(curr_val)
            if not np.isfinite(curr_val):
                raise ValueError(f"{code} measurements must be finite when present")
            features[f"{code}_curr"] = curr_val
            features[f"{code}_missing"] = 0.0

            # Historical series for this analyte. Missing values never become zero.
            series = []
            for obs in history:
                value = obs.get("analytes", {}).get(code)
                if value is None or pd.isna(value):
                    continue
                if isinstance(value, (bool, np.bool_)):
                    raise ValueError(f"{code} measurements must be numeric, not boolean")
                value = float(value)
                if not np.isfinite(value):
                    raise ValueError(f"{code} measurements must be finite when present")
                series.append((float(obs["day"]), value))

            # 90-day slope (velocity)
            recent_series = [(d, v) for d, v in series if (current_day - d) <= 90.0]
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
                t1, y1 = series[-3]
                t2, y2 = series[-2]
                t3, y3 = series[-1]
                slope_early = (y2 - y1) / (t2 - t1)
                slope_late = (y3 - y2) / (t3 - t2)
                accel = 2.0 * (slope_late - slope_early) / (t3 - t1)
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
                if mean_v > 0:
                    features[f"{code}_cv"] = float(std_v / mean_v)
                    features[f"{code}_cv_available"] = 1.0
                else:
                    features[f"{code}_cv"] = float("nan")
                    features[f"{code}_cv_available"] = 0.0
            else:
                features[f"{code}_cv"] = float("nan")
                features[f"{code}_cv_available"] = 0.0

        return features

    def transform_cohort(
        self,
        patients_df: pd.DataFrame,
        observations_df: pd.DataFrame,
        horizon_days: float,
        *,
        synthetic_only: bool | None = None,
    ) -> Tuple[pd.DataFrame, pd.Series, np.ndarray, np.ndarray]:
        """
        Transforms full cohort into feature matrix X, prospective binary label y,
        follow-up times, and event indicators for survival modeling.
        """
        if isinstance(horizon_days, (bool, np.bool_)) or not np.isscalar(horizon_days):
            raise ValueError("horizon_days must be a finite positive number, not boolean")
        try:
            horizon_days = float(horizon_days)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("horizon_days must be finite and positive") from exc
        if not np.isfinite(horizon_days) or horizon_days <= 0:
            raise ValueError("horizon_days must be finite and positive")
        if synthetic_only is not None and not isinstance(synthetic_only, (bool, np.bool_)):
            raise ValueError("synthetic_only must be boolean when supplied")
        required_observation_columns = {"patient_id", "day"}
        missing_observation_columns = required_observation_columns - set(observations_df.columns)
        if missing_observation_columns:
            raise ValueError(
                "observations are missing required columns: "
                f"{sorted(missing_observation_columns)}"
            )
        required_outcome_columns = {"patient_id", "observed_recurrence_event"}
        missing_outcome_columns = required_outcome_columns - set(patients_df.columns)
        if missing_outcome_columns:
            raise ValueError(
                "patient outcome data is missing required columns: "
                f"{sorted(missing_outcome_columns)}"
            )
        if patients_df["patient_id"].isna().any() or observations_df["patient_id"].isna().any():
            raise ValueError("patient_id must be present in patient and observation rows")
        if patients_df["patient_id"].duplicated().any():
            raise ValueError("patients_df must contain exactly one row per patient_id")
        unknown_patient_ids = set(observations_df["patient_id"]) - set(patients_df["patient_id"])
        if unknown_patient_ids:
            raise ValueError(f"observations reference unknown patient_ids: {sorted(unknown_patient_ids)}")
        pt_dict = {row["patient_id"]: row.to_dict() for _, row in patients_df.iterrows()}

        # Group observations by patient
        grouped_obs: Dict[str, List[Dict[str, Any]]] = {}
        for _, row in observations_df.iterrows():
            pt_id = row["patient_id"]
            if isinstance(row["day"], (bool, np.bool_)):
                raise ValueError(f"observation day must be numeric, not boolean for patient {pt_id}")
            analytes: Dict[str, float] = {}
            for code in self.tracked_analytes:
                mask_column = f"observed_{code}"
                has_value_column = code in row.index
                value = row[code] if has_value_column else None
                value_present = has_value_column and pd.notna(value)

                if mask_column in row.index:
                    mask = row[mask_column]
                    valid_mask = isinstance(mask, (bool, np.bool_)) or (
                        isinstance(mask, (int, np.integer, float, np.floating))
                        and np.isfinite(mask)
                        and mask in (0, 1)
                    )
                    if not valid_mask:
                        raise ValueError(
                            f"{mask_column} must be a non-null boolean or 0/1 for patient {pt_id}"
                        )
                    if bool(mask) != bool(value_present):
                        raise ValueError(
                            f"{mask_column} disagrees with {code} value presence for patient {pt_id}"
                        )
                    if not bool(mask):
                        continue

                if value_present:
                    if isinstance(value, (bool, np.bool_)):
                        raise ValueError(f"{code} measurements must be numeric, not boolean")
                    numeric_value = float(value)
                    if not np.isfinite(numeric_value):
                        raise ValueError(f"{code} measurements must be finite when present")
                    analytes[code] = numeric_value

            obs_dict = {
                "day": float(row["day"]),
                "analytes": analytes,
                "symptoms": (
                    {
                        col.replace("symptom_", ""): row[col]
                        for col in row.index
                        if col.startswith("symptom_")
                    }
                    or None
                ),
            }
            if "treatment_active" in row.index:
                treatment = row["treatment_active"]
                treatment_missing = treatment is None or (
                    pd.api.types.is_scalar(treatment) and pd.isna(treatment)
                )
                if not treatment_missing and (
                    not isinstance(treatment, str) or not treatment.strip()
                ):
                    raise ValueError(
                        "treatment_active must be a non-empty treatment name or missing"
                    )
                obs_dict["treatment_active"] = treatment
                obs_dict["_treatment_status_available"] = True
            grouped_obs.setdefault(pt_id, []).append(obs_dict)

        for pt_id, obs_list in grouped_obs.items():
            days = np.asarray([obs["day"] for obs in obs_list], dtype=float)
            if not np.isfinite(days).all():
                raise ValueError(f"observation days must be finite for patient {pt_id}")
            if len(np.unique(days)) != len(days):
                raise ValueError(f"duplicate observation day for patient {pt_id}")

        features_list = []
        labels_list = []
        follow_up_times = []
        event_indicators = []

        for pt_id, obs_list in grouped_obs.items():
            pt_row = pt_dict.get(pt_id)
            if not pt_row:
                continue

            rec_event_value = pt_row.get("observed_recurrence_event")
            valid_bool = isinstance(rec_event_value, (bool, np.bool_))
            valid_binary = (
                isinstance(rec_event_value, (int, np.integer, float, np.floating))
                and not isinstance(rec_event_value, (bool, np.bool_))
                and np.isfinite(rec_event_value)
                and rec_event_value in (0, 1)
            )
            if pd.isna(rec_event_value) or not (valid_bool or valid_binary):
                raise ValueError(
                    f"observed_recurrence_event must be a non-null boolean or 0/1 for patient {pt_id}"
                )
            rec_event = bool(rec_event_value)
            rec_day = pt_row.get("observed_recurrence_day")
            if not rec_event and rec_day is not None and not pd.isna(rec_day):
                raise ValueError(f"recurrence day supplied without an observed event for patient {pt_id}")
            comp_day = pt_row.get("competing_event_day")
            comp_type = pt_row.get("competing_event")
            has_comp_type = comp_type is not None and not pd.isna(comp_type)
            if has_comp_type and (
                not isinstance(comp_type, str)
                or comp_type not in SUPPORTED_COMPETING_EVENTS
            ):
                raise ValueError(
                    f"unsupported competing event type {comp_type!r} for patient {pt_id}"
                )
            has_comp_day = comp_day is not None and not pd.isna(comp_day)
            if rec_event and (rec_day is None or pd.isna(rec_day)):
                raise ValueError(f"observed recurrence day is required for patient {pt_id}")
            if has_comp_type != has_comp_day:
                raise ValueError(
                    f"competing event type and day must be supplied together for patient {pt_id}"
                )
            for field, value in (
                ("observed_recurrence_day", rec_day),
                ("competing_event_day", comp_day),
            ):
                if isinstance(value, (bool, np.bool_)):
                    raise ValueError(f"{field} must be numeric, not boolean for patient {pt_id}")
            terminal_days = [
                float(day)
                for day in (rec_day if rec_event else None, comp_day if has_comp_day else None)
                if day is not None and not pd.isna(day)
            ]
            if any(not np.isfinite(day) or day < 0 for day in terminal_days):
                raise ValueError(f"event days must be finite and non-negative for patient {pt_id}")
            if len(terminal_days) == 2 and terminal_days[0] == terminal_days[1]:
                raise ValueError(f"recurrence and competing event cannot share a day for patient {pt_id}")
            if (
                rec_event
                and has_comp_day
                and comp_type != "lost_to_follow_up"
                and float(comp_day) < float(rec_day)
            ):
                raise ValueError(f"observed recurrence follows a terminal competing event for patient {pt_id}")
            last_day = max(o["day"] for o in obs_list)
            admin_end = pt_row.get("administrative_censor_day")
            if admin_end is None or pd.isna(admin_end):
                admin_end = last_day
            elif isinstance(admin_end, (bool, np.bool_)):
                raise ValueError(
                    f"administrative_censor_day must be numeric, not boolean for patient {pt_id}"
                )
            admin_end = float(admin_end)
            if not np.isfinite(admin_end) or admin_end < last_day:
                raise ValueError(
                    f"observations extend beyond administrative follow-up for patient {pt_id}"
                )
            if (
                has_comp_type
                and comp_type != "lost_to_follow_up"
                and float(comp_day) < last_day
            ):
                raise ValueError(f"observations extend beyond a competing event for patient {pt_id}")
            if has_comp_type and comp_type == "lost_to_follow_up" and float(comp_day) < last_day:
                raise ValueError(f"observations extend beyond loss to follow-up for patient {pt_id}")
            # A configured event time beyond administrative follow-up is not an
            # observed event in this cohort; administrative censoring wins.
            if rec_event and float(rec_day) > admin_end:
                raise ValueError(f"observed recurrence occurs after administrative follow-up for patient {pt_id}")

            for obs in obs_list:
                d = obs["day"]

                # Exclude visits occurring after competing event
                if comp_day is not None and not np.isnan(comp_day) and d >= comp_day:
                    continue
                # Exclude visits on or after clinical recurrence was confirmed.
                if rec_event and rec_day is not None and not np.isnan(rec_day) and d >= rec_day:
                    continue

                feat = self.extract_features_at_visit(
                    pt_row, obs_list, d, synthetic_only=synthetic_only
                )
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
                if not np.isfinite(float(admin_end)) or float(admin_end) < last_day:
                    raise ValueError(
                        f"observations extend beyond administrative follow-up for patient {pt_id}"
                    )
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
                    time_to_event_or_censor = max(0.0, event_day - d)
                else:
                    censor_day = min(
                        float(admin_end),
                        float(comp_day) if lost_to_follow_up else float(admin_end),
                    )
                    time_to_event_or_censor = max(0.0, censor_day - d)

                # The binary horizon label is known for observed recurrence or a
                # competing event within H, or when follow-up covers all of H.
                # A loss/admin censor before H is unknown, never a negative label.
                if event_flag == 1 and time_to_event_or_censor <= horizon_days:
                    y_label = 1.0
                elif event_flag == 2 and time_to_event_or_censor <= horizon_days:
                    y_label = 0.0
                elif time_to_event_or_censor >= horizon_days or (
                    event_flag != 0 and time_to_event_or_censor > horizon_days
                ):
                    y_label = 0.0
                else:
                    y_label = np.nan

                features_list.append(feat)
                labels_list.append(y_label)
                follow_up_times.append(time_to_event_or_censor)
                event_indicators.append(event_flag)

        X = pd.DataFrame(features_list)
        y = pd.Series(
            labels_list,
            dtype=float,
            name=f"observed_diagnosis_within_{int(horizon_days)}d",
        )
        y.attrs["target_estimand"] = "observed_diagnosis"
        y.attrs["horizon_days"] = float(horizon_days)
        if synthetic_only is not None:
            y.attrs["synthetic_only"] = bool(synthetic_only)

        return X, y, np.array(follow_up_times), np.array(event_indicators)


def build_landmark_features(
    observations_df: pd.DataFrame,
    patients_df: Optional[pd.DataFrame] = None,
    *,
    horizon_days: float,
    synthetic_only: bool | None = None,
) -> Tuple[pd.DataFrame, pd.Series, np.ndarray, np.ndarray]:
    """Build landmarks for an explicitly selected target horizon."""
    extractor = WindowedFeatureExtractor()
    if patients_df is None:
        raise ValueError(
            "patients_df with observed outcome metadata is required to construct horizon labels"
        )
    return extractor.transform_cohort(
        patients_df=patients_df,
        observations_df=observations_df,
        horizon_days=horizon_days,
        synthetic_only=synthetic_only,
    )


build_features = build_landmark_features


