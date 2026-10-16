#!/usr/bin/env python3
"""
scripts/train_k1_amortized.py

Committed reproducible training script for Model K1 Amortized Recognition Network (RR13).
Trains AmortizedRecognitionNet on forward simulator draws and saves the canonical
safetensors weights to packages/vigil-ml/vigil_ml/models/k1_amortized_weights.safetensors.
"""

from __future__ import annotations

from pathlib import Path

from safetensors.torch import save_file
from vigil_ml.k1 import (
    AMORTIZED_WEIGHTS_PATH,
    AmortizedRecognitionNet,
    train_amortized,
)

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    print("🚀 Training Model K1 Amortized Recognition Network (seed=42, epochs=35)...")
    res = train_amortized(n_sims=3000, seed=42, shuffle_pairs=False, epochs=35)
    model: AmortizedRecognitionNet = res["model"]

    print(f"Initial training loss: {res['train_loss'][0]:.4f}, final: {res['train_loss'][-1]:.4f}")
    print(f"Initial validation loss: {res['val_loss'][0]:.4f}, final: {res['val_loss'][-1]:.4f}")

    AMORTIZED_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_file(model.state_dict(), str(AMORTIZED_WEIGHTS_PATH))
    print(f"✅ Saved trained weights to {AMORTIZED_WEIGHTS_PATH} ({AMORTIZED_WEIGHTS_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
