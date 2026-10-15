"""
Model A Trainer: Baseline Organ Susceptibility Profiler (Legacy Prototype)

NOTICE: This prototype training script is DEPRECATED per MASTER_PLAN.md §14 WP0.3
and §15 (Defect A2). Valid baseline organ tropism models calibrated to literature
and SEER priors are introduced in Phase 2.
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import pickle
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb

from vigil_api.ml.synthetic_generator import generate_synthetic_cohort


def extract_baseline_dataset(patients: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Extracts feature matrix X and target matrix Y from synthetic cohort."""
    X_list = []
    Y_list = []

    for p in patients:
        features = [
            float(p["age"]),
            float(p["tumor_stage"]),
            1.0 if p["er_status"] else 0.0,
            1.0 if p["pr_status"] else 0.0,
            1.0 if p["her2_status"] else 0.0,
            1.0 if p["has_hypertension"] else 0.0,
            1.0 if p["renal_history"] else 0.0,
        ]
        vec = p["target_organ_susceptibility_vector"]
        targets = [
            float(vec["bone"]),
            float(vec["liver"]),
            float(vec["lung"]),
            float(vec["brain"]),
        ]
        X_list.append(features)
        Y_list.append(targets)

    return np.array(X_list, dtype=np.float32), np.array(Y_list, dtype=np.float32)


def train_baseline_model(
    artifacts_dir: str | None = None,
) -> None:
    """Trains and serializes Model A."""
    if artifacts_dir is None:
        artifacts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    print("Generating 1,000 synthetic patient records for robust Model A training...")
    patients, _ = generate_synthetic_cohort(num_patients=1000)

    X, Y = extract_baseline_dataset(patients)
    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

    print(f"Training set: {X_train.shape[0]} patients, Test set: {X_test.shape[0]} patients.")

    model = xgb.XGBRegressor(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        n_jobs=1,
        random_state=42,
    )
    model.fit(X_train, Y_train)

    # Evaluation
    Y_pred = model.predict(X_test)
    mse = mean_squared_error(Y_test, Y_pred)
    r2 = r2_score(Y_test, Y_pred)
    print(f"Model A (XGBoost) Test MSE: {mse:.5f}, R2 Score: {r2:.4f}")

    # Output normalization wrapper function check
    sample_pred = Y_pred[0]
    sample_norm = np.maximum(sample_pred, 0.01) / np.sum(np.maximum(sample_pred, 0.01))
    print(f"Sample normalized organ susceptibility output: {sample_norm} (Sum: {np.sum(sample_norm):.2f})")

    save_path = os.path.join(artifacts_dir, "baseline_model.pkl")
    with open(save_path, "wb") as f:
        pickle.dump(model, f)
    print(f"Saved Model A to {save_path}")


if __name__ == "__main__":
    train_baseline_model()
