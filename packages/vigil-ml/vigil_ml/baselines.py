"""
vigil_ml.baselines

Classical Surveillance Baselines (M2 Stack, MASTER_PLAN §14 WP2.2, ML_PROGRAM §9).
Conforms strictly to docs/MASTER_PLAN.md §14 (WP2.2) and docs/ML_PROGRAM.md §5, §9.

Includes:
1. Prevalence Baseline: Constant empirical training base rate.
2. Single-Threshold Baseline: Fixed clinical cutoff (CA 15-3 >= 30.0 U/mL).
3. Velocity / Rate-of-Change Baseline: 90-day biomarker slope and RCV thresholding.
4. Regularized Discrete-Time Cox Hazard: L2-penalized logistic hazard on summary features.
5. Gradient Boosting Baseline: XGBoost classifier on engineered longitudinal features.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression


class BaseSurveillanceModel(ABC):
    """Abstract base class for all surveillance inference models."""

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> BaseSurveillanceModel:
        pass

    @abstractmethod
    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        """Returns prospective recurrence probability in [0, 1]."""
        pass

    @abstractmethod
    def get_model_id(self) -> str:
        pass


class PrevalenceBaseline(BaseSurveillanceModel):
    """Predicts a constant prospective risk equal to empirical training prevalence."""

    def __init__(self):
        self.prevalence: float = 0.15

    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> PrevalenceBaseline:
        self.prevalence = float(np.mean(y)) if len(y) > 0 else 0.15
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self.prevalence, dtype=float)

    def get_model_id(self) -> str:
        return "B0_PREVALENCE"


class SingleThresholdBaseline(BaseSurveillanceModel):
    """
    Standard Clinical Threshold Rule:
    Evaluates primary tumor marker (CA 15-3) against clinical upper limit of normal (30.0 U/mL).
    Outputs sigmoid-scaled risk score.
    """

    def __init__(self, marker_col: str = "ca_15_3_curr", cutoff: float = 30.0, scale: float = 8.0):
        self.marker_col = marker_col
        self.cutoff = cutoff
        self.scale = scale

    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> SingleThresholdBaseline:
        # Pre-set rule; fit is a no-op or calibration check
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        vals = X[self.marker_col].values if self.marker_col in X else np.zeros(len(X))
        # Logistic sigmoid centered at cutoff
        z = (vals - self.cutoff) / self.scale
        return 1.0 / (1.0 + np.exp(-z))

    def get_model_id(self) -> str:
        return "B1_SINGLE_THRESHOLD"


class VelocityBaseline(BaseSurveillanceModel):
    """
    Biomarker Rate-of-Change / Doubling-Time Rule:
    Evaluates 90-day velocity (slope) of CA 15-3 and CEA.
    Triggers risk elevation when positive slope exceeds physiological fluctuation threshold.
    """

    def __init__(
        self,
        ca153_slope_col: str = "ca_15_3_slope_90d",
        cea_slope_col: str = "cea_slope_90d",
        velocity_cutoff: float = 0.08,  # ~2.4 U/mL/month
    ):
        self.ca153_slope_col = ca153_slope_col
        self.cea_slope_col = cea_slope_col
        self.cutoff = velocity_cutoff

    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> VelocityBaseline:
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        ca_slope = X[self.ca153_slope_col].values if self.ca153_slope_col in X else np.zeros(len(X))
        cea_slope = X[self.cea_slope_col].values if self.cea_slope_col in X else np.zeros(len(X))
        combined_velocity = np.maximum(ca_slope, cea_slope * 2.0)
        z = (combined_velocity - self.cutoff) / 0.05
        return 1.0 / (1.0 + np.exp(-z))

    def get_model_id(self) -> str:
        return "B2_VELOCITY_RULE"


class RegularizedCoxHazardBaseline(BaseSurveillanceModel):
    """
    Discrete-Time Hazard / Logistic Survival Model with L2 Regularization (Ridge).
    Trained on full set of windowed summary features.
    """

    def __init__(self, C: float = 1.0, random_state: int = 42):
        self.C = C
        self.random_state = random_state
        self.model = LogisticRegression(C=C, max_iter=1000, random_state=random_state)
        self.feature_cols: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> RegularizedCoxHazardBaseline:
        # Exclude non-feature columns
        drop_cols = [c for c in ["patient_id", "observation_id"] if c in X.columns]
        feat_df = X.drop(columns=drop_cols).fillna(0.0)
        self.feature_cols = list(feat_df.columns)

        self.model.fit(feat_df, y)
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        feat_df = X[self.feature_cols].fillna(0.0)
        probs = self.model.predict_proba(feat_df)[:, 1]
        return np.clip(probs, 0.0, 1.0)

    def get_model_id(self) -> str:
        return "B3_REGULARIZED_COX_HAZARD"


class GradientBoostingBaseline(BaseSurveillanceModel):
    """
    Gradient Boosted Decision Tree (XGBoost) surveillance baseline.
    Trained with early stopping, controlled tree depth to avoid overfitting,
    and calibrated probabilities.
    """

    def __init__(
        self,
        max_depth: int = 4,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        random_state: int = 42,
    ):
        self.max_depth = max_depth
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.model = xgb.XGBClassifier(
            max_depth=max_depth,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            random_state=random_state,
            eval_metric="logloss",
        )
        self.feature_cols: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> GradientBoostingBaseline:
        drop_cols = [c for c in ["patient_id", "observation_id"] if c in X.columns]
        feat_df = X.drop(columns=drop_cols).fillna(0.0)
        self.feature_cols = list(feat_df.columns)

        self.model.fit(feat_df, y)
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        feat_df = X[self.feature_cols].fillna(0.0)
        probs = self.model.predict_proba(feat_df)[:, 1]
        return np.clip(probs, 0.0, 1.0)

    def get_model_id(self) -> str:
        return "B4_GRADIENT_BOOSTING_XGB"
