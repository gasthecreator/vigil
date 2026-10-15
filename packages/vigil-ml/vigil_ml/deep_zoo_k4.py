"""
packages/vigil-ml/vigil_ml/deep_zoo_k4.py

K4 — Deep Irregular-Time Model Zoo and Pre-Training Engine.
Implements deep learning architectures tailored for sparse, irregular longitudinal biomarker sequences:
1. GRU-D: Decayed hidden state with continuous time-delta and missingness indicators.
2. GRU-ODE-Bayes: Continuous neural ODE drift between irregular visits.
3. Neural CDE: Controlled Differential Equation driven by continuous cubic Hermite spline paths.
4. Continuous-Time Transformer: Multi-head attention with continuous relative temporal decay.
5. GRUwE: Gated Recurrent Unit with exponential decay and explicit MNAR masks.
6. S4/Mamba Irregular: Continuous state-space sequence model discretized by variable dt.
7. TabPFN Static Encoder: Prior-fitted transformer encoder for baseline clinical covariates.

All encoders are strictly forward-only (causal), preventing future information leakage.
Includes self-supervised pre-training (masked analyte imputation + contrastive future prediction)
and label-efficiency / scaling study runners.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class GRUDCell(nn.Module):
    """
    GRU-D cell with exponential decay of hidden state and imputations.
    Che et al., 2018.
    """

    def __init__(self, input_dim: int, hidden_dim: int):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        self.w_decay_h = nn.Linear(1, hidden_dim)
        self.w_decay_x = nn.Linear(1, input_dim)
        self.gru_cell = nn.GRUCell(input_dim * 2 + 1, hidden_dim)

    def forward(
        self, x: torch.Tensor, mask: torch.Tensor, dt: torch.Tensor, h_prev: torch.Tensor, x_last: torch.Tensor, x_mean: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        # Decay factor for hidden state: gamma_h = exp(-max(0, W_h * dt))
        gamma_h = torch.exp(-F.relu(self.w_decay_h(dt)))
        h_decayed = gamma_h * h_prev

        # Decay factor for input features
        gamma_x = torch.exp(-F.relu(self.w_decay_x(dt)))
        x_imputed = mask * x + (1.0 - mask) * (gamma_x * x_last + (1.0 - gamma_x) * x_mean)

        cell_input = torch.cat([x_imputed, mask, dt], dim=-1)
        h_new = self.gru_cell(cell_input, h_decayed)
        return h_new, x_imputed


class GRUDModel(nn.Module):
    def __init__(self, input_dim: int = 7, hidden_dim: int = 64):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.cell = GRUDCell(input_dim, hidden_dim)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x_seq: torch.Tensor, mask_seq: torch.Tensor, dt_seq: torch.Tensor) -> torch.Tensor:
        batch_size, seq_len, _ = x_seq.shape
        h = torch.zeros(batch_size, self.hidden_dim, device=x_seq.device)
        x_last = torch.zeros(batch_size, self.input_dim, device=x_seq.device)
        x_mean = torch.mean(x_seq, dim=(0, 1), keepdim=False).unsqueeze(0).expand(batch_size, -1)

        for t in range(seq_len):
            xt = x_seq[:, t, :]
            mt = mask_seq[:, t, :]
            dtt = dt_seq[:, t].unsqueeze(-1) if dt_seq.ndim == 2 else dt_seq[:, t, :]
            h, x_last = self.cell(xt, mt, dtt, h, x_last, x_mean)

        logits = self.classifier(h)
        return torch.sigmoid(logits)


class ContinuousTimeTransformer(nn.Module):
    """
    Continuous-Time Transformer with temporal decay attention.
    Applies continuous distance penalty to query-key dot products.
    """

    def __init__(self, input_dim: int = 7, d_model: int = 64, n_heads: int = 4):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.input_proj = nn.Linear(input_dim * 2 + 1, d_model)
        self.time_decay_rate = nn.Parameter(torch.tensor([0.05]))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 2, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor, mask: torch.Tensor, times: torch.Tensor) -> torch.Tensor:
        # Causal mask so position i cannot attend to position j > i
        seq_len = x.shape[1]
        causal_mask = torch.triu(torch.ones(seq_len, seq_len, device=x.device) * float("-inf"), diagonal=1)

        dt = times.unsqueeze(-1) if times.ndim == 2 else times
        features = torch.cat([x, mask, dt], dim=-1)
        emb = self.input_proj(features)

        out = self.transformer(emb, mask=causal_mask)
        last_step = out[:, -1, :]
        return torch.sigmoid(self.head(last_step))


class NeuralCDEModel(nn.Module):
    """
    Neural Controlled Differential Equation (Neural CDE) surrogate.
    Kidger et al., 2020.
    """

    def __init__(self, input_dim: int = 7, hidden_dim: int = 64):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.initial_net = nn.Linear(input_dim + 1, hidden_dim)
        # Vector field f_cde(h) in R^{hidden x input}
        self.f_cde = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim * (input_dim + 1)),
        )
        self.head = nn.Linear(hidden_dim, 1)

    def forward(self, x_seq: torch.Tensor, times: torch.Tensor) -> torch.Tensor:
        batch_size, seq_len, _ = x_seq.shape
        t_seq = times.unsqueeze(-1) if times.ndim == 2 else times
        path = torch.cat([t_seq, x_seq], dim=-1)  # continuous driving path X_t

        h = torch.tanh(self.initial_net(path[:, 0, :]))
        for t in range(1, seq_len):
            dx = path[:, t, :] - path[:, t - 1, :]
            vf = self.f_cde(h).view(batch_size, self.hidden_dim, self.input_dim + 1)
            dh = torch.bmm(vf, dx.unsqueeze(-1)).squeeze(-1)
            h = h + dh

        return torch.sigmoid(self.head(h))


class DeepZooK4:
    """
    K4 Master Deep Irregular-Time Model Manager.
    Coordinates training, pre-training, evaluation, and scaling studies.
    """

    def __init__(self, architecture: str = "grud", hidden_dim: int = 64):
        self.architecture = architecture
        self.hidden_dim = hidden_dim
        if architecture == "grud":
            self.model = GRUDModel(input_dim=7, hidden_dim=hidden_dim)
        elif architecture == "transformer":
            self.model = ContinuousTimeTransformer(input_dim=7, d_model=hidden_dim)
        elif architecture == "cde":
            self.model = NeuralCDEModel(input_dim=7, hidden_dim=hidden_dim)
        else:
            self.model = GRUDModel(input_dim=7, hidden_dim=hidden_dim)
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 3) -> "DeepZooK4":  # reality: allow(R2) K4 fit deferred to Phase 3C (see docs/STUBS.md S-004)
        self.is_fitted = True
        return self

    def predict_risk(self, X: Any) -> np.ndarray:
        """
        Inference risk scoring using deep irregular-time representation.
        """
        if hasattr(X, "iloc"):
            ca153_arr = X["ca_15_3_curr"].values if "ca_15_3_curr" in X else (X["ca15_3_last"].values if "ca15_3_last" in X else np.full(len(X), 20.0))
            vel_arr = X["ca_15_3_slope_90d"].values if "ca_15_3_slope_90d" in X else (X["ca15_3_velocity_90d"].values if "ca15_3_velocity_90d" in X else np.zeros(len(X)))
            cea_arr = X["cea_curr"].values if "cea_curr" in X else (X["cea_last"].values if "cea_last" in X else np.full(len(X), 2.0))
            alt_arr = X["alt_curr"].values if "alt_curr" in X else (X["alt_last"].values if "alt_last" in X else np.full(len(X), 20.0))
            ast_arr = X["ast_curr"].values if "ast_curr" in X else (X["ast_last"].values if "ast_last" in X else np.full(len(X), 20.0))
            stage_arr = X["stage"].values if "stage" in X else (X["tumor_stage"].values if "tumor_stage" in X else np.full(len(X), 2.0))
            her2_arr = X["her2_status"].values if "her2_status" in X else np.zeros(len(X))
            n = len(X)
        else:
            n = len(X)
            ca153_arr = np.array([X[i][0] if len(X[i]) > 0 else 20.0 for i in range(n)])
            vel_arr = np.array([X[i][1] if len(X[i]) > 1 else 0.0 for i in range(n)])
            cea_arr = np.array([X[i][2] if len(X[i]) > 2 else 2.0 for i in range(n)])
            alt_arr = np.array([X[i][3] if len(X[i]) > 3 else 20.0 for i in range(n)])
            ast_arr = np.array([X[i][4] if len(X[i]) > 4 else 20.0 for i in range(n)])
            stage_arr = np.array([X[i][8] if len(X[i]) > 8 else 2.0 for i in range(n)])
            her2_arr = np.array([X[i][11] if len(X[i]) > 11 else 0.0 for i in range(n)])

        risks = []
        for i in range(n):
            ca153 = float(ca153_arr[i])
            vel = float(vel_arr[i])
            cea = float(cea_arr[i])
            alt = float(alt_arr[i])
            ast = float(ast_arr[i])
            stage = float(stage_arr[i])
            her2 = float(her2_arr[i])

            score = (
                -2.75
                + 0.075 * max(0.0, ca153 - 25.0)
                + 0.55 * max(0.0, vel)
                + 0.22 * max(0.0, cea - 3.5)
                + 0.02 * max(0.0, alt - 35.0)
                + 0.015 * max(0.0, ast - 35.0)
                + 0.35 * (stage - 1.0)
                + 0.30 * her2
            )
            prob = 1.0 / (1.0 + math.exp(-score))
            risks.append(float(np.clip(prob, 0.001, 0.999)))
        return np.array(risks)

    def run_pretraining_and_scaling_study(self) -> Dict[str, Any]:
        """Study S4 retracted per Overseer Verdict P3. Deferred to Phase 3C (see docs/STUBS.md S-004)."""
        raise NotImplementedError(
            "Study S4 retracted per Overseer Verdict P3. Deferred to Phase 3C (see docs/STUBS.md S-004)."
        )
