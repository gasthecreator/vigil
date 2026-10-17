"""
vigil_eval.leakage

Reusable Data Leakage Detection Suite for Vigil Oncology Platform.
Enforces Master Plan §7.3 and §14 (WP1.4).

Detects:
1. Patient-level split leakage (ID overlap across train/val/test)
2. Temporal future leakage (features computed from future observation timestamps)
3. Outcome-derived feature leakage (forbidden substring tokens, near-perfect target correlation > 0.999)
4. Preprocessing / Scaler fit leakage (scalers fit on evaluation folds)
5. Shuffled-label canary test (proves model collapses to chance ~0.50 ROC-AUC under permuted labels)
"""

from __future__ import annotations

import re
from typing import Any, Callable, List, Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold


class LeakageError(Exception):
    """Base exception for data leakage violations."""

    pass


class PatientSplitLeakageError(LeakageError):
    """Raised when patient identifiers leak across train, validation, or test partitions."""

    pass


class TemporalLeakageError(LeakageError):
    """Raised when observation timestamps post-date the prediction reference time."""

    pass


class OutcomeDerivedFeatureError(LeakageError):
    """Raised when features contain target-derived information or forbidden anomaly tokens."""

    pass


class PreprocessingLeakageError(LeakageError):
    """Raised when scalers, imputers, or encoders are fitted on evaluation data."""

    pass


class CanaryTestFailedError(LeakageError):
    """Raised when a model trained on shuffled labels fails to collapse to chance performance."""

    pass


class UnobservedValueLeakageError(LeakageError):
    """Raised when unmeasured/unobserved analyte values leak into observation exports or features."""

    pass


DEFAULT_FORBIDDEN_TOKENS = [
    "is_anomaly",
    "anomaly",
    "label",
    "target",
    "outcome",
    "recurrence",
    "metastasis_occurred",
    "event_day",
    "time_to_event",
    "vital_status",
    "death",
]


def check_patient_split_leakage(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    val_df: Optional[pd.DataFrame] = None,
    id_col: str = "patient_id",
) -> None:
    """
    Verifies that no patient identifiers overlap between train, validation, and test datasets.
    """
    if id_col not in train_df.columns:
        raise ValueError(f"ID column '{id_col}' missing from train_df")
    if id_col not in test_df.columns:
        raise ValueError(f"ID column '{id_col}' missing from test_df")

    train_ids = set(train_df[id_col].dropna().unique())
    test_ids = set(test_df[id_col].dropna().unique())

    overlap_train_test = train_ids.intersection(test_ids)
    if overlap_train_test:
        sample = list(overlap_train_test)[:5]
        raise PatientSplitLeakageError(
            f"Patient split leakage detected! {len(overlap_train_test)} patient IDs present in "
            f"both train and test sets. Sample overlapping IDs: {sample}"
        )

    if val_df is not None:
        if id_col not in val_df.columns:
            raise ValueError(f"ID column '{id_col}' missing from val_df")
        val_ids = set(val_df[id_col].dropna().unique())

        overlap_train_val = train_ids.intersection(val_ids)
        if overlap_train_val:
            sample = list(overlap_train_val)[:5]
            raise PatientSplitLeakageError(
                f"Patient split leakage detected! {len(overlap_train_val)} patient IDs present in "
                f"both train and validation sets. Sample: {sample}"
            )

        overlap_val_test = val_ids.intersection(test_ids)
        if overlap_val_test:
            sample = list(overlap_val_test)[:5]
            raise PatientSplitLeakageError(
                f"Patient split leakage detected! {len(overlap_val_test)} patient IDs present in "
                f"both validation and test sets. Sample: {sample}"
            )


def check_temporal_future_leakage(
    df: pd.DataFrame,
    prediction_time_col: str,
    feature_time_cols: List[str],
) -> None:
    """
    Verifies that every feature timestamp is strictly <= prediction reference time.
    """
    if prediction_time_col not in df.columns:
        raise ValueError(f"Prediction time column '{prediction_time_col}' missing from dataframe")

    pred_times = pd.to_numeric(df[prediction_time_col], errors="coerce")
    for time_col in feature_time_cols:
        if time_col not in df.columns:
            continue
        feat_times = pd.to_numeric(df[time_col], errors="coerce")
        violations = feat_times > pred_times
        if violations.any():
            count = violations.sum()
            sample_idx = df[violations].index.tolist()[:3]
            raise TemporalLeakageError(
                f"Temporal future leakage detected in column '{time_col}'! {count} rows have "
                f"feature timestamps exceeding prediction time '{prediction_time_col}'. Row indices: {sample_idx}"
            )


def check_outcome_derived_features(
    X: pd.DataFrame,
    y: Optional[pd.Series] = None,
    forbidden_tokens: Optional[List[str]] = None,
    max_correlation: float = 0.999,
) -> None:
    """
    Scans feature matrix for forbidden target tokens and near-perfect correlation with outcome.
    """
    tokens = forbidden_tokens or DEFAULT_FORBIDDEN_TOKENS

    # 1. Lexical static check
    for col in X.columns:
        col_lower = str(col).lower()
        for tok in tokens:
            # Check for exact token or word boundaries
            if re.search(rf"\b{re.escape(tok)}\b", col_lower) or tok in col_lower:
                raise OutcomeDerivedFeatureError(
                    f"Forbidden outcome-derived token '{tok}' detected in feature column name '{col}'."
                )

    # 2. Mathematical correlation check if target is provided
    if y is not None:
        y_num = pd.to_numeric(y, errors="coerce")
        # Check numeric features
        for col in X.select_dtypes(include=[np.number]).columns:
            x_col = X[col]
            if x_col.std() == 0 or y_num.std() == 0:
                continue
            corr = abs(x_col.corr(y_num))
            if corr >= max_correlation:
                raise OutcomeDerivedFeatureError(
                    f"Outcome-derived correlation leakage detected! Feature '{col}' has Pearson correlation "
                    f"|r| = {corr:.6f} with target (threshold: {max_correlation})."
                )


def check_scaler_fit_leakage(
    fitted_scaler: Any,
    test_X: pd.DataFrame | np.ndarray,
    tolerance: float = 1e-4,
) -> None:
    """
    Checks if a scaler was accidentally fit on the test/evaluation fold.
    Raises PreprocessingLeakageError if the scaler's fitted attributes exactly match test set statistics.
    """
    arr = test_X.to_numpy() if isinstance(test_X, pd.DataFrame) else np.asarray(test_X)

    # Check StandardScaler (mean_)
    if hasattr(fitted_scaler, "mean_"):
        test_mean = np.nanmean(arr, axis=0)
        scaler_mean = fitted_scaler.mean_
        if np.allclose(test_mean, scaler_mean, atol=tolerance):
            raise PreprocessingLeakageError(
                "Scaler fit leakage detected! Scaler fitted mean_ matches test set empirical mean exactly."
            )

    # Check MinMaxScaler (data_min_, data_max_)
    if hasattr(fitted_scaler, "data_min_") and hasattr(fitted_scaler, "data_max_"):
        test_min = np.nanmin(arr, axis=0)
        test_max = np.nanmax(arr, axis=0)
        if np.allclose(test_min, fitted_scaler.data_min_, atol=tolerance) and np.allclose(
            test_max, fitted_scaler.data_max_, atol=tolerance
        ):
            raise PreprocessingLeakageError(
                "Scaler fit leakage detected! Scaler fitted bounds match test set bounds exactly."
            )


def run_shuffled_label_canary(
    X: pd.DataFrame,
    y: pd.Series,
    model_factory: Optional[Callable[[], BaseEstimator]] = None,
    n_splits: int = 3,
    max_tolerated_auc: float = 0.60,
    seed: int = 42,
) -> float:
    """
    Shuffles target labels and runs cross-validation.
    Performance must collapse to chance (~0.50 ROC-AUC).
    If ROC-AUC exceeds max_tolerated_auc, raises CanaryTestFailedError.
    """
    np.random.default_rng(seed)
    y_shuffled = y.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    X_clean = X.reset_index(drop=True).select_dtypes(include=[np.number]).fillna(0.0)

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    auc_scores = []

    for train_idx, test_idx in kf.split(X_clean):
        X_train, X_test = X_clean.iloc[train_idx], X_clean.iloc[test_idx]
        y_train, y_test = y_shuffled.iloc[train_idx], y_shuffled.iloc[test_idx]

        clf = (
            model_factory()
            if model_factory
            else LogisticRegression(max_iter=200, random_state=seed)
        )
        clf.fit(X_train, y_train)

        # Probabilities
        if hasattr(clf, "predict_proba"):
            preds = clf.predict_proba(X_test)[:, 1]
        else:
            preds = clf.decision_function(X_test)

        score = roc_auc_score(y_test, preds)
        auc_scores.append(score)

    mean_auc = float(np.mean(auc_scores))

    if mean_auc > max_tolerated_auc:
        raise CanaryTestFailedError(
            f"Shuffled-label canary FAILED! Model achieved ROC-AUC = {mean_auc:.4f} on permuted labels "
            f"(threshold: <= {max_tolerated_auc}). Indicates severe data leakage or degenerate features."
        )

    return mean_auc


def run_unobserved_value_canary(observations_df: pd.DataFrame) -> dict[str, int]:
    """
    Leakage canary test verifying that unobserved values are strictly NaN in observation exports.
    Latent ground truth must never leak into model-visible analyte columns.
    Raises UnobservedValueLeakageError if any unmeasured observation contains non-NaN data.
    """
    masks = [c for c in observations_df.columns if c.startswith("observed_")]
    if not masks:
        return {}

    checked_counts: dict[str, int] = {}
    for m in masks:
        col = m[len("observed_") :]
        if col not in observations_df.columns:
            continue
        unobs = ~observations_df[m].astype(bool)
        unobs_count = int(unobs.sum())
        checked_counts[col] = unobs_count
        leaked = int(observations_df.loc[unobs, col].notna().sum())
        if leaked > 0:
            raise UnobservedValueLeakageError(
                f"Unobserved-value canary FAILED! {leaked} unmeasured observations in '{col}' "
                f"contain non-NaN values (out of {unobs_count} unobserved instances)."
            )

    return checked_counts


def run_latent_column_canary(feature_df: pd.DataFrame) -> None:
    """
    Verifies that no ground-truth latent state columns or raw target indicators
    appear in model feature inputs.
    """
    forbidden_prefixes = ("latent_", "true_")
    violating_cols = [c for c in feature_df.columns if any(c.startswith(p) for p in forbidden_prefixes)]
    if violating_cols:
        raise OutcomeDerivedFeatureError(
            f"Latent column canary FAILED! Latent or ground-truth columns leaked into feature matrix: {violating_cols}"
        )

