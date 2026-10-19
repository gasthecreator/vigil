"""
vigil_ml.baselines

Classical Surveillance Baselines (M2 Stack, MASTER_PLAN §14 WP2.2, ML_PROGRAM §9).
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.2) and docs/ML_PROGRAM.md §5, §9.

Includes:
1. Prevalence Baseline: Constant empirical training base rate.
2. Single-Threshold Baseline: Registry-sourced CA 15-3 reference cutoff.
3. Velocity / Rate-of-Change Baseline: 90-day biomarker slope and RCV thresholding.
4. Regularized Logistic Baseline: L2-penalized binary horizon model on summary features.
5. Gradient Boosting Baseline: XGBoost classifier on engineered longitudinal features.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from vigil_core.analytes import ANALYTE_REGISTRY


def _prepare_classifier_training_data(
    X: pd.DataFrame,
    y: pd.Series,
    sample_weight: np.ndarray | None,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray | None]:
    """Validate horizon labels and keep censored outcomes from becoming negatives."""
    labels = np.asarray(y, dtype=float)
    if len(labels) != len(X):
        raise ValueError("X and y must have the same number of rows")
    weights = None if sample_weight is None else np.asarray(sample_weight, dtype=float)
    if weights is not None and len(weights) != len(labels):
        raise ValueError("sample_weight must have the same length as y")
    if np.any(~np.isfinite(labels)) and weights is None:
        raise ValueError(
            "Horizon labels contain censored outcomes; provide IPCW sample_weight and event metadata"
        )
    if not np.isfinite(labels[~np.isnan(labels)]).all() or np.any(
        ~np.isin(labels[~np.isnan(labels)], [0.0, 1.0])
    ):
        raise ValueError("Observed classification labels must be finite binary values")
    valid = np.isfinite(labels)
    if weights is not None:
        if not np.isfinite(weights).all() or np.any(weights < 0):
            raise ValueError("sample_weight must be finite and non-negative")
        valid &= weights > 0
    if not np.any(valid):
        raise ValueError("No observed, positively weighted horizon labels are available")
    y_valid = labels[valid].astype(int)
    if np.unique(y_valid).size < 2:
        raise ValueError("Training data must contain both horizon outcome classes")
    x_valid = X.loc[valid].drop(columns=[c for c in ("patient_id", "observation_id") if c in X])
    x_valid = x_valid.replace([np.inf, -np.inf], np.nan)
    weight_valid = weights[valid] if weights is not None else None
    return x_valid, y_valid, weight_valid


def _training_prevalence(y: pd.Series, sample_weight: np.ndarray | None) -> float:
    labels = np.asarray(y, dtype=float)
    if np.isinf(labels).any():
        raise ValueError("Horizon labels must not contain infinite values")
    weights = None if sample_weight is None else np.asarray(sample_weight, dtype=float)
    if weights is not None and len(weights) != len(labels):
        raise ValueError("sample_weight must have the same length as y")
    if np.any(~np.isfinite(labels)) and weights is None:
        raise ValueError("Censored horizon labels require IPCW sample_weight")
    valid = np.isfinite(labels)
    if not np.isin(labels[valid], [0.0, 1.0]).all():
        raise ValueError("Observed horizon labels must be binary")
    if weights is not None:
        if not np.isfinite(weights).all() or np.any(weights < 0):
            raise ValueError("sample_weight must be finite and non-negative")
        valid &= weights > 0
    if not np.any(valid):
        raise ValueError("No observed, positively weighted horizon labels are available")
    return float(np.average(labels[valid], weights=weights[valid]) if weights is not None else labels[valid].mean())


class BaseSurveillanceModel(ABC):
    """Base interface for model scores; probability claims require calibration."""

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> BaseSurveillanceModel:  # reality: stateless
        pass

    @abstractmethod
    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        """Returns a prospective score in [0, 1]; it is not necessarily calibrated."""
        pass

    @abstractmethod
    def get_model_id(self) -> str:
        pass


class PrevalenceBaseline(BaseSurveillanceModel):
    """Predicts a constant prospective risk equal to empirical training prevalence."""

    def __init__(self):
        self.prevalence: float | None = None

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: np.ndarray | None = None,
        **kwargs,
    ) -> PrevalenceBaseline:
        self.prevalence = _training_prevalence(y, sample_weight)
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        if self.prevalence is None:
            raise RuntimeError("PrevalenceBaseline must be fitted before prediction")
        return np.full(len(X), self.prevalence, dtype=float)

    def get_model_id(self) -> str:
        return "B0_PREVALENCE"


class SingleThresholdBaseline(BaseSurveillanceModel):
    """
    Registry-threshold comparator for the primary tumor marker (CA 15-3).
    Returns a binary rule score, with missing-marker rows using fitted weighted prevalence.
    """

    def __init__(self, marker_col: str = "ca_15_3_curr", cutoff: float | None = None):
        self.marker_col = marker_col
        self.cutoff = (
            ANALYTE_REGISTRY["ca_15_3"].plausibility.reference_high
            if cutoff is None
            else cutoff
        )
        self.fallback_prevalence: float | None = None

    def fit(
        self, X: pd.DataFrame, y: pd.Series, sample_weight: np.ndarray | None = None, **kwargs
    ) -> SingleThresholdBaseline:
        self.fallback_prevalence = _training_prevalence(y, sample_weight)
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        if self.fallback_prevalence is None:
            raise RuntimeError("SingleThresholdBaseline must be fitted before prediction")
        vals = X[self.marker_col].to_numpy(dtype=float) if self.marker_col in X else np.full(len(X), np.nan)
        scores = (vals >= self.cutoff).astype(float)
        missing = ~np.isfinite(vals)
        if f"{self.marker_col.removesuffix('_curr')}_missing" in X:
            missing |= X[f"{self.marker_col.removesuffix('_curr')}_missing"].to_numpy(dtype=bool)
        scores[missing] = self.fallback_prevalence
        return scores

    def get_model_id(self) -> str:
        return "B1_SINGLE_THRESHOLD"


class VelocityBaseline(BaseSurveillanceModel):
    """
    Legacy biomarker velocity comparator using its declared fixed rule parameters.
    These parameters are research assumptions and lack clinical validation.
    """

    def __init__(
        self,
        ca153_slope_col: str = "ca_15_3_slope_90d",
        cea_slope_col: str = "cea_slope_90d",
        velocity_cutoff: float = 0.08,
    ):
        self.ca153_slope_col = ca153_slope_col
        self.cea_slope_col = cea_slope_col
        self.cutoff = velocity_cutoff
        self.fallback_prevalence: float | None = None

    def fit(
        self, X: pd.DataFrame, y: pd.Series, sample_weight: np.ndarray | None = None, **kwargs
    ) -> VelocityBaseline:
        self.fallback_prevalence = _training_prevalence(y, sample_weight)
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        if self.fallback_prevalence is None:
            raise RuntimeError("VelocityBaseline must be fitted before prediction")
        ca_slope = X[self.ca153_slope_col].to_numpy(dtype=float) if self.ca153_slope_col in X else np.full(len(X), np.nan)
        cea_slope = X[self.cea_slope_col].to_numpy(dtype=float) if self.cea_slope_col in X else np.full(len(X), np.nan)
        ca_available = np.isfinite(ca_slope)
        cea_available = np.isfinite(cea_slope)
        if "ca_15_3_slope_90d_available" in X:
            ca_available &= X["ca_15_3_slope_90d_available"].to_numpy(dtype=bool)
        if "cea_slope_90d_available" in X:
            cea_available &= X["cea_slope_90d_available"].to_numpy(dtype=bool)
        combined_velocity = np.full(len(X), np.nan)
        has_velocity = ca_available | cea_available
        combined_velocity[has_velocity] = np.maximum(
            np.where(ca_available[has_velocity], ca_slope[has_velocity], -np.inf),
            np.where(cea_available[has_velocity], cea_slope[has_velocity] * 2.0, -np.inf),
        )
        scores = (combined_velocity >= self.cutoff).astype(float)
        unavailable = ~has_velocity
        scores[unavailable] = self.fallback_prevalence
        return scores

    def get_model_id(self) -> str:
        return "B2_VELOCITY_RULE"


class RegularizedCoxHazardBaseline(BaseSurveillanceModel):
    """
    L2-regularized logistic classifier for the configured horizon label.

    Despite the compatibility class name, this is not a Cox model and does not
    estimate a time-varying hazard.
    """

    def __init__(self, C: float = 1.0, random_state: int = 42):
        self.C = C
        self.random_state = random_state
        self.scaler = None
        self.imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        self.model = LogisticRegression(
            C=C, max_iter=2000, random_state=random_state, solver="lbfgs"
        )
        self.feature_cols: List[str] = []

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: np.ndarray | None = None,
        **kwargs,
    ) -> RegularizedCoxHazardBaseline:
        feat_df, labels, weights = _prepare_classifier_training_data(X, y, sample_weight)
        self.feature_cols = list(feat_df.columns)

        self.scaler = StandardScaler()
        imputed_X = self.imputer.fit_transform(feat_df)
        scaled_X = self.scaler.fit_transform(imputed_X)
        self.model.fit(scaled_X, labels, sample_weight=weights)
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        if self.scaler is None:
            raise RuntimeError("RegularizedCoxHazardBaseline must be fitted before prediction")
        missing = set(self.feature_cols) - set(X.columns)
        if missing:
            raise ValueError(f"Prediction data is missing training features: {sorted(missing)}")
        feat_df = X[self.feature_cols].replace([np.inf, -np.inf], np.nan)
        imputed_X = self.imputer.transform(feat_df)
        scaled_X = self.scaler.transform(imputed_X) if self.scaler is not None else imputed_X
        probs = self.model.predict_proba(scaled_X)[:, 1]
        return np.clip(probs, 0.0, 1.0)

    def get_model_id(self) -> str:
        return "B3_REGULARIZED_LOGISTIC_HORIZON"


class GradientBoostingBaseline(BaseSurveillanceModel):
    """
    Gradient Boosted Decision Tree (XGBoost) surveillance baseline.
    Trained with controlled tree depth. Probability calibration is performed
    separately on a disjoint calibration cohort.
    """

    def __init__(
        self,
        max_depth: int = 4,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        random_state: int = 42,
        n_jobs: int = 1,
    ):
        self.max_depth = max_depth
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.model = xgb.XGBClassifier(
            max_depth=max_depth,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            random_state=random_state,
            n_jobs=n_jobs,
            objective="binary:logistic",
            eval_metric="logloss",
        )
        self.feature_cols: List[str] = []
        self.imputer = SimpleImputer(strategy="median", keep_empty_features=True)

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: np.ndarray | None = None,
        **kwargs,
    ) -> GradientBoostingBaseline:
        feat_df, labels, weights = _prepare_classifier_training_data(X, y, sample_weight)
        self.feature_cols = list(feat_df.columns)

        imputed_X = self.imputer.fit_transform(feat_df)
        self.model.fit(imputed_X, labels, sample_weight=weights)
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        if not self.feature_cols:
            raise RuntimeError("GradientBoostingBaseline must be fitted before prediction")
        missing = set(self.feature_cols) - set(X.columns)
        if missing:
            raise ValueError(f"Prediction data is missing training features: {sorted(missing)}")
        feat_df = X[self.feature_cols].replace([np.inf, -np.inf], np.nan)
        imputed_X = self.imputer.transform(feat_df)
        probs = self.model.predict_proba(imputed_X)[:, 1]
        return np.clip(probs, 0.0, 1.0)

    def get_model_id(self) -> str:
        return "B4_XGBOOST_HORIZON"
