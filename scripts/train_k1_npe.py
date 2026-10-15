#!/usr/bin/env python3
"""Train and save the K1 Neural Posterior Estimator for amortized and NPE routes."""

from pathlib import Path

import numpy as np
import torch
from sbi.inference import NPE_C
from sbi.utils import BoxUniform

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS_PATH = ROOT / "packages" / "vigil-ml" / "vigil_ml" / "models" / "k1_npe_weights.pt"

SCHEDULE = np.array([0.0, 60.0, 120.0, 180.0, 240.0, 300.0, 360.0])

prior_min = torch.tensor([40.0, 0.05, 0.05, 30.0])
prior_max = torch.tensor([160.0, 0.35, 0.20, 240.0])
prior = BoxUniform(low=prior_min, high=prior_max)

def simulator(theta):
    N = theta.shape[0]
    out = np.zeros((N, len(SCHEDULE)))
    for i in range(N):
        T_d = float(theta[i, 0])
        s = float(theta[i, 1])
        c = float(theta[i, 2])
        t_onset = float(theta[i, 3])
        g = np.log(2.0) / T_d
        dt = np.maximum(0.0, SCHEDULE - t_onset)
        elev = np.where(SCHEDULE >= t_onset, (s * 1.0) / (g + c) * (np.exp(g * dt) - np.exp(-c * dt)), 0.0)
        mu = 18.0 + elev
        out[i] = mu + np.random.normal(0, 1.5, size=len(SCHEDULE))
    return torch.tensor(out, dtype=torch.float32)

print("Simulating 5000 training pairs for K1 NPE...")
torch.manual_seed(42)
np.random.seed(42)
theta_train = prior.sample((5000,))
x_train = simulator(theta_train)

print("Training NPE_C...")
inference = NPE_C(prior=prior)
inference.append_simulations(theta_train, x_train)
density_estimator = inference.train(training_batch_size=128, max_num_epochs=60)

print(f"Saving trained density estimator to {WEIGHTS_PATH}...")
torch.save(density_estimator, str(WEIGHTS_PATH))
print("Done!")
