"""Historical K3 compatibility names and the logistic landmark research baseline.

The registered Bayesian joint model is not implemented here. The former
BayesianJointModelK3 implementation is quarantined and fails closed.
"""

from __future__ import annotations

from typing import Any, List, Optional

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from vigil_ml.baselines import BaseSurveillanceModel, _prepare_classifier_training_data


class BayesianJointModelK3(BaseSurveillanceModel):
    """Compatibility name for a quarantined, invalid historical K3 implementation.

    The former sampler did not implement the registered patient-grouped,
    competing-risk joint model. It returned posterior-looking quantities and
    risk scores from unsupported assumptions, so all execution fails closed.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Accept legacy constructor arguments so callers get the actionable
        # quarantine error at fit/predict rather than an unrelated TypeError.
        self._legacy_arguments = (args, kwargs)

    @staticmethod
    def _quarantined() -> RuntimeError:
        return RuntimeError(
            "BayesianJointModelK3 is quarantined: this historical implementation "
            "is not the registered joint model and cannot produce valid inference"
        )

    def fit(
        self, X: pd.DataFrame, y: pd.Series, **kwargs: Any
    ) -> BayesianJointModelK3:
        raise self._quarantined()

    def check_posterior_predictive(self, X: pd.DataFrame) -> None:
        raise self._quarantined()

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        raise self._quarantined()

    def get_model_id(self) -> str:
        return "K3_QUARANTINED_INVALID_HISTORICAL_IMPLEMENTATION"


_LANDMARK_FEATURE_COLUMNS = (
    "ca_15_3_curr",
    "ca_15_3_slope_90d",
    "cea_curr",
    "age",
    "is_stage_3_or_4",
    "sub_tnbc",
    "max_symptom_grade",
)


class LandmarkLogisticResearchBaseline(BaseSurveillanceModel):
    """
    Fast landmark logistic research baseline (legacy K3-compatible class name).

    The fitted prediction path is a regularized logistic classifier over landmark
    features. This is neither a Bayesian joint model nor a production model.
    The supplied labels define the target horizon.
    """

    def __init__(self, C: float = 1.0, random_state: int = 42):
        self.C = C
        self.random_state = random_state

        # Learned binary horizon-score model; independent calibration is external.
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        self.classifier = LogisticRegression(
            C=C, max_iter=2000, random_state=random_state, solver="lbfgs"
        )
        self.is_fitted = False
        self.feature_names_: List[str] = [
            *_LANDMARK_FEATURE_COLUMNS,
            *(f"{column}_missing" for column in _LANDMARK_FEATURE_COLUMNS),
        ]
        self.fitted_coef_: Optional[np.ndarray] = None
        self.fitted_intercept_: Optional[float] = None

    def _extract_landmark_features(self, X: pd.DataFrame) -> np.ndarray:
        # Missing columns and missing measurements remain missing until the
        # training-fitted imputer handles them; they are never assigned assumed values.
        def values(column: str) -> np.ndarray:
            return pd.to_numeric(X[column], errors="coerce").to_numpy(dtype=float) if column in X else np.full(len(X), np.nan)

        raw_features = np.column_stack([values(column) for column in _LANDMARK_FEATURE_COLUMNS])
        missing_indicators = (~np.isfinite(raw_features)).astype(float)
        return np.column_stack([raw_features, missing_indicators])

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weight: np.ndarray | None = None,
        **kwargs: Any,
    ) -> LandmarkLogisticResearchBaseline:
        """Fit a logistic classifier to the supplied binary horizon labels."""
        if kwargs:
            raise TypeError(f"Unsupported fit options: {sorted(kwargs)}")

        feat_df, labels, weights = _prepare_classifier_training_data(X, y, sample_weight)
        X_fit = X.loc[feat_df.index]
        feat_mat = self._extract_landmark_features(X_fit)
        imputed_feat = self.imputer.fit_transform(feat_mat)
        scaled_feat = self.scaler.fit_transform(imputed_feat)

        self.classifier.fit(scaled_feat, labels, sample_weight=weights)
        self.fitted_coef_ = self.classifier.coef_[0]
        self.fitted_intercept_ = float(self.classifier.intercept_[0])
        self.is_fitted = True

        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        """Return the fitted logistic score; calibration is not implied."""
        if not self.is_fitted:
            raise RuntimeError("LandmarkLogisticResearchBaseline must be fitted before prediction")
        feat_mat = self._extract_landmark_features(X)
        imputed_feat = self.imputer.transform(feat_mat)
        scaled_feat = self.scaler.transform(imputed_feat)
        return np.asarray(
            np.clip(self.classifier.predict_proba(scaled_feat)[:, 1], 0.0, 1.0), dtype=float
        )

    def get_model_id(self) -> str:
        return "FAST_LANDMARK_LOGISTIC_RESEARCH"


class FastLandmarkJointModel(LandmarkLogisticResearchBaseline):
    """Legacy constructor retained for frozen experiment source compatibility."""

    def __init__(
        self,
        horizon_days: float = 180.0,
        C: float = 1.0,
        random_state: int = 42,
    ):
        # The historical argument never changed the label horizon; keep accepting
        # it for old callers while the canonical API omits this misleading option.
        super().__init__(C=C, random_state=random_state)
