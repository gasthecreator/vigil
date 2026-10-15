"""
Model B Trainer: Longitudinal Anomaly Detector (Legacy Prototype)

NOTICE: This prototype training script is DEPRECATED per MASTER_PLAN.md §14 WP0.3
and §15 (Defects A1, A2, A3). It uses circular is_anomaly labels and an acausal
BiLSTM. Valid causal forecasting models are introduced in Phase 2 and Phase 3.
"""

import os
import pickle
import random

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset

from vigil_api.ml.models import LongitudinalLSTM
from vigil_api.ml.synthetic_generator import generate_synthetic_cohort


class LongitudinalTrajectoryDataset(Dataset):
    """PyTorch Dataset for padded longitudinal biomarker sequences."""

    def __init__(
        self,
        sequences: list[np.ndarray],
        labels: list[float],
        max_len: int = 20,
    ):
        self.max_len = max_len
        self.data = []
        self.masks = []
        self.labels = []

        for seq, label in zip(sequences, labels):
            seq_len = len(seq)
            if seq_len > max_len:
                seq = seq[-max_len:]
                seq_len = max_len

            # Pad sequence
            padded = np.zeros((max_len, seq.shape[1]), dtype=np.float32)
            padded[:seq_len] = seq

            mask = np.zeros(max_len, dtype=bool)
            mask[:seq_len] = True

            self.data.append(padded)
            self.masks.append(mask)
            self.labels.append(float(label))

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return (
            torch.tensor(self.data[idx], dtype=torch.float32),
            torch.tensor(self.masks[idx], dtype=torch.bool),
            torch.tensor([self.labels[idx]], dtype=torch.float32),
        )


def build_sequence_dataset(
    patients: list[dict],
    all_labs: list[dict],
    scaler: StandardScaler | None = None,
    fit_scaler: bool = True,
) -> tuple[list[np.ndarray], list[float], StandardScaler]:
    """
    Builds sequential training examples including prefix sequences to train
    the model for real-time turn-by-turn monitoring.
    """
    # Group labs by patient_id
    labs_by_patient: dict[str, list[dict]] = {}
    for lab in all_labs:
        p_id = lab["patient_id"]
        labs_by_patient.setdefault(p_id, []).append(lab)

    patient_map = {p["patient_id"]: p for p in patients}

    # Collect all raw lab values for scaling
    if fit_scaler:
        raw_labs_matrix = []
        for lab in all_labs:
            raw_labs_matrix.append(
                [
                    lab["alt_level"],
                    lab["ast_level"],
                    lab["creatinine"],
                    lab["ca_15_3"],
                    lab["wbc_count"],
                ]
            )
        scaler = StandardScaler()
        scaler.fit(raw_labs_matrix)

    sequences = []
    labels = []

    for p_id, p_labs in labs_by_patient.items():
        patient = patient_map[p_id]
        p_labs_sorted = sorted(p_labs, key=lambda x: x["date_drawn"])
        organ_vec = patient["target_organ_susceptibility_vector"]
        susc_arr = np.array(
            [
                organ_vec["bone"],
                organ_vec["liver"],
                organ_vec["lung"],
                organ_vec["brain"],
            ],
            dtype=np.float32,
        )

        # Build prefixes for dynamic monitoring (e.g. at visit 2, visit 3, etc.)
        for k in range(2, len(p_labs_sorted) + 1):
            sub_labs = p_labs_sorted[:k]
            last_lab = sub_labs[-1]

            # Label is positive if this prefix ends in an anomaly sequence
            label = 1.0 if last_lab.get("is_anomaly", False) else 0.0

            step_vectors = []
            for lab in sub_labs:
                raw_lab = np.array(
                    [
                        [
                            lab["alt_level"],
                            lab["ast_level"],
                            lab["creatinine"],
                            lab["ca_15_3"],
                            lab["wbc_count"],
                        ]
                    ]
                )
                scaled_lab = scaler.transform(raw_lab)[0]
                combined = np.concatenate([scaled_lab, susc_arr], axis=0)  # dim = 9
                step_vectors.append(combined)

            sequences.append(np.array(step_vectors, dtype=np.float32))
            labels.append(label)

    return sequences, labels, scaler


def train_lstm_model(
    artifacts_dir: str | None = None,
) -> None:
    """Trains and serializes Model B."""
    if artifacts_dir is None:
        artifacts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)

    print("Generating 600 synthetic patient trajectories for Model B training...")
    cohort_patients, cohort_labs = generate_synthetic_cohort(num_patients=600, recurrence_rate=0.30)

    # Train / test patient split
    random.shuffle(cohort_patients)
    split_idx = int(len(cohort_patients) * 0.8)
    train_patients = cohort_patients[:split_idx]
    test_patients = cohort_patients[split_idx:]

    train_patient_ids = {p["patient_id"] for p in train_patients}
    test_patient_ids = {p["patient_id"] for p in test_patients}

    train_labs = [lab for lab in cohort_labs if lab["patient_id"] in train_patient_ids]
    test_labs = [lab for lab in cohort_labs if lab["patient_id"] in test_patient_ids]

    train_seqs, train_labels, scaler = build_sequence_dataset(
        train_patients, train_labs, fit_scaler=True
    )
    test_seqs, test_labels, _ = build_sequence_dataset(
        test_patients, test_labs, scaler=scaler, fit_scaler=False
    )

    print(
        f"Generated {len(train_seqs)} training sequence prefixes and {len(test_seqs)} test sequence prefixes."
    )
    pos_train = sum(train_labels)
    print(
        f"Positive anomaly instances in train: {pos_train}/{len(train_labels)} ({pos_train / len(train_labels) * 100:.1f}%)"
    )

    train_dataset = LongitudinalTrajectoryDataset(train_seqs, train_labels)
    test_dataset = LongitudinalTrajectoryDataset(test_seqs, test_labels)

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else ("mps" if torch.backends.mps.is_available() else "cpu")
    )
    print(f"Training Model B on computing device: {device}")

    model = LongitudinalLSTM(input_size=9, hidden_size=32, num_layers=2, dropout=0.2).to(device)

    # Weighted loss for anomaly detection
    torch.tensor([(len(train_labels) - pos_train) / max(pos_train, 1.0)]).to(device)
    criterion = nn.BCELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=25)

    best_val_auc = 0.0
    best_weights = None

    for epoch in range(1, 26):
        model.train()
        total_loss = 0.0

        for x_b, mask_b, y_b in train_loader:
            x_b, mask_b, y_b = x_b.to(device), mask_b.to(device), y_b.to(device)
            optimizer.zero_grad()

            risk_pred, _ = model(x_b, mask=mask_b)
            loss = criterion(risk_pred, y_b)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += loss.item() * len(y_b)

        scheduler.step()
        train_loss = total_loss / len(train_dataset)

        # Validation
        model.eval()
        val_preds, val_targets = [], []
        with torch.no_grad():
            for x_b, mask_b, y_b in test_loader:
                x_b, mask_b = x_b.to(device), mask_b.to(device)
                risk_pred, _ = model(x_b, mask=mask_b)
                val_preds.extend(risk_pred.cpu().numpy().flatten())
                val_targets.extend(y_b.numpy().flatten())

        val_auc = roc_auc_score(val_targets, val_preds) if len(set(val_targets)) > 1 else 0.5
        val_acc = accuracy_score(val_targets, [p >= 0.5 for p in val_preds])

        if val_auc > best_val_auc:
            best_val_auc = val_auc
            best_weights = model.state_dict().copy()

        if epoch % 5 == 0 or epoch == 25:
            print(
                f"Epoch {epoch:02d}/25 - Train Loss: {train_loss:.4f} - Val AUC: {val_auc:.4f} - Val Acc: {val_acc:.4f}"
            )

    print(f"Best Validation ROC-AUC for Model B: {best_val_auc:.4f}")

    # Save artifacts
    weights_path = os.path.join(artifacts_dir, "longitudinal_lstm.pt")
    scaler_path = os.path.join(artifacts_dir, "feature_scalers.pkl")

    torch.save(best_weights or model.state_dict(), weights_path)
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    print(f"Saved Model B weights to {weights_path}")
    print(f"Saved feature scaler to {scaler_path}")


if __name__ == "__main__":
    train_lstm_model()
