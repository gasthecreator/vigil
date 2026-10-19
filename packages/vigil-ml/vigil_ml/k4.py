"""vigil_ml.k4: deep irregular-time risk models (K4) with masked-analyte pre-training.

Six forward-only encoder families share one interface and one training loop:
GRU-D, GRU-ODE-Bayes (deterministic encoder), Neural CDE (linear path, Euler), a continuous-time transformer,
GRUwE (E24) and an irregular-time selective state-space model. The prediction for a visit is read from the state
at that visit, so a prediction never depends on a later visit (tested). Pre-registered study:
`experiments/EXP-K4-001/PREREG.md`.

Input convention (arrays only; this module imports no simulator and never reads a `latent_*` or `observed_*`
column): per patient, up to `MAX_STEPS` visits with analyte values `x` (log of value over a fixed reference
midpoint), observed mask `m`, visit day `t`, static vector `s` and a `valid` flag for real (non-padded) visits.

Model exchange is safetensors plus ONNX. Weights are never serialised as Python objects.

Not built (stated in the PREREG): TabPFN-style prior-fitted networks, the contrastive pre-training objective, the
adjoint and log-signature options of Neural CDE, the variational observation model of GRU-ODE-Bayes.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ANALYTES: Tuple[str, ...] = (
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
)
SYMPTOMS: Tuple[str, ...] = (
    "bone_pain",
    "jaundice",
    "ruq_pain",
    "cough_dyspnea",
    "headache_neuro",
    "fatigue_weight_loss",
)
N_LAB = len(ANALYTES)
N_CHANNELS = N_LAB + len(SYMPTOMS)  # laboratory channels first (log-scaled, maskable), then symptom grades / 4
SYMPTOM_SCALE = 4.0
N_STATIC = 8
MAX_STEPS = 24
FAMILIES: Tuple[str, ...] = ("grud", "gru_ode_bayes", "neural_cde", "ct_transformer", "gruwe", "ssm")
SIZES: Dict[str, int] = {"small": 16, "medium": 32, "large": 64}
FORMAT = "vigil-k4-v1"
DAY_SCALE = 90.0  # visit gaps are measured in units of 90 days inside the networks
ABS_SCALE = 365.0


# ---------------------------------------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------------------------------------
@dataclass
class SequenceSet:
    """Padded sequences. Shapes: x, m [P, T, A]; t, valid [P, T]; s [P, S]. Optional labels y, row_mask [P, T]."""

    patient_ids: List[str]
    x: np.ndarray
    m: np.ndarray
    t: np.ndarray
    s: np.ndarray
    valid: np.ndarray
    y: Optional[np.ndarray] = None
    row_mask: Optional[np.ndarray] = None

    def __len__(self) -> int:
        return len(self.patient_ids)

    @property
    def lengths(self) -> np.ndarray:
        return self.valid.sum(axis=1).astype(int)

    def subset(self, idx: Sequence[int]) -> "SequenceSet":
        idx = np.asarray(idx, dtype=int)
        return SequenceSet(
            [self.patient_ids[i] for i in idx],
            self.x[idx],
            self.m[idx],
            self.t[idx],
            self.s[idx],
            self.valid[idx],
            None if self.y is None else self.y[idx],
            None if self.row_mask is None else self.row_mask[idx],
        )


def log_reference(value: np.ndarray, reference_mid: np.ndarray) -> np.ndarray:
    """The fixed input scaling: clip(log(value / reference midpoint), -5, 5). Never fitted."""
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.log(np.asarray(value, dtype=float) / reference_mid)
    return np.clip(np.nan_to_num(z, nan=0.0, posinf=5.0, neginf=-5.0), -5.0, 5.0)


def build_sequences(
    patient_ids: Sequence[str],
    days: Sequence[Sequence[float]],
    values: Sequence[np.ndarray],
    statics: np.ndarray,
    reference_mid: np.ndarray,
    max_steps: int = MAX_STEPS,
) -> SequenceSet:
    """Pad per-patient visit lists. `values[i]` is [n_visits_i, C] with NaN for a channel not drawn.

    The first `len(reference_mid)` columns are laboratory values (log-scaled against the fixed reference midpoints);
    any further columns (symptom grades) are used as given. A patient with more than `max_steps` visits raises (the
    study never truncates silently).
    """
    P, n_lab = len(patient_ids), len(reference_mid)
    C = np.asarray(values[0]).shape[-1] if P else n_lab
    x = np.zeros((P, max_steps, C), dtype=np.float32)
    m = np.zeros((P, max_steps, C), dtype=np.float32)
    t = np.zeros((P, max_steps), dtype=np.float32)
    valid = np.zeros((P, max_steps), dtype=bool)
    for i in range(P):
        d = np.asarray(days[i], dtype=float)
        v = np.asarray(values[i], dtype=float).reshape(len(d), C)
        if len(d) > max_steps:
            raise ValueError(f"patient {patient_ids[i]} has {len(d)} visits; max_steps is {max_steps}")
        order = np.argsort(d, kind="stable")
        d, v = d[order], v[order]
        n = len(d)
        obs = ~np.isnan(v)
        scaled = np.where(obs, v, 0.0)
        scaled[:, :n_lab] = np.where(obs[:, :n_lab], log_reference(np.where(obs[:, :n_lab], v[:, :n_lab], 1.0), reference_mid), 0.0)
        x[i, :n] = scaled
        m[i, :n] = obs
        t[i, :n] = d
        if n:
            t[i, n:] = d[-1]
        valid[i, :n] = True
    return SequenceSet(list(patient_ids), x, m, t, np.asarray(statics, dtype=np.float32), valid)


def attach_labels(ds: SequenceSet, rows: Dict[Tuple[str, float], float]) -> SequenceSet:
    """Attach landmark labels: `rows[(patient_id, visit_day)] = y`. Only visits that have a row are scored."""
    y = np.zeros(ds.valid.shape, dtype=np.float32)
    mask = np.zeros(ds.valid.shape, dtype=bool)
    for i, pid in enumerate(ds.patient_ids):
        n = int(ds.valid[i].sum())
        for j in range(n):
            key = (pid, float(ds.t[i, j]))
            if key in rows:
                y[i, j] = rows[key]
                mask[i, j] = True
    return SequenceSet(ds.patient_ids, ds.x, ds.m, ds.t, ds.s, ds.valid, y, mask)


# ---------------------------------------------------------------------------------------------------------
# Encoders. Every encoder maps (x, m, t, s, valid) to states [B, T, H]; state j depends only on visits <= j.
# ---------------------------------------------------------------------------------------------------------
def _time_inputs(t: torch.Tensor, valid: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """Gap to the previous visit in 90-day units (0 at the first visit and at padding) and absolute time/365."""
    prev = torch.cat([t[:, :1], t[:, :-1]], dim=1)
    dt = torch.clamp((t - prev) / DAY_SCALE, 0.0, 10.0) * valid
    return dt, t / ABS_SCALE


def _context(s: torch.Tensor, t_abs: torch.Tensor) -> torch.Tensor:
    T = t_abs.shape[1]
    return torch.cat([s.unsqueeze(1).expand(-1, T, -1), t_abs.unsqueeze(-1)], dim=-1)


def _hold(valid_j: torch.Tensor, new: torch.Tensor, old: torch.Tensor) -> torch.Tensor:
    v = valid_j
    while v.dim() < new.dim():
        v = v.unsqueeze(-1)
    return v * new + (1.0 - v) * old


class GRUD(nn.Module):
    """GRU-D (Che et al. 2018): decayed hidden state, decayed imputation towards the last value and the mean."""

    def __init__(self, hidden: int, n_a: int, n_s: int):
        super().__init__()
        self.hidden, self.n_a = hidden, n_a
        self.decay_h = nn.Linear(1, hidden)
        self.decay_x = nn.Linear(1, n_a)
        self.cell = nn.GRUCell(2 * n_a + n_s + 1 + 1, hidden)

    def forward(self, x, m, t, s, valid):
        B, T, A = x.shape
        dt, t_abs = _time_inputs(t, valid)
        ctx = _context(s, t_abs)
        h = x.new_zeros(B, self.hidden)
        last = x.new_zeros(B, A)
        outs = []
        for j in range(T):
            d = dt[:, j : j + 1]
            gh = torch.exp(-F.relu(self.decay_h(d)))
            gx = torch.exp(-F.relu(self.decay_x(d)))
            xj, mj = x[:, j] * m[:, j], m[:, j]
            x_hat = mj * xj + (1.0 - mj) * (gx * last)  # the analyte mean is 0 on the standardised scale
            inp = torch.cat([x_hat, mj, ctx[:, j], d], dim=-1)
            h_new = self.cell(inp, gh * h)
            v = valid[:, j]
            h = _hold(v, h_new, h)
            last = _hold(v, mj * xj + (1.0 - mj) * last, last)
            outs.append(h)
        return torch.stack(outs, dim=1)


class GRUODEBayes(nn.Module):
    """GRU-ODE-Bayes encoder (De Brouwer et al. 2019): the GRU-ODE flow between visits, a GRU update at a visit."""

    def __init__(self, hidden: int, n_a: int, n_s: int, substeps: int = 4):
        super().__init__()
        self.hidden, self.substeps = hidden, substeps
        self.lin_r, self.lin_z, self.lin_g = (nn.Linear(hidden, hidden) for _ in range(3))
        self.update = nn.GRUCell(2 * n_a + n_s + 1, hidden)

    def _f(self, h):
        r = torch.sigmoid(self.lin_r(h))
        z = torch.sigmoid(self.lin_z(h))
        g = torch.tanh(self.lin_g(r * h))
        return (1.0 - z) * (g - h)

    def _flow(self, h, dt):
        step = (dt / self.substeps).unsqueeze(-1) if dt.dim() == 1 else dt / self.substeps
        for _ in range(self.substeps):
            k1 = self._f(h)
            k2 = self._f(h + 0.5 * step * k1)
            k3 = self._f(h + 0.5 * step * k2)
            k4 = self._f(h + step * k3)
            h = h + step / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        return h

    def forward(self, x, m, t, s, valid):
        B, T, _ = x.shape
        dt, t_abs = _time_inputs(t, valid)
        ctx = _context(s, t_abs)
        h = x.new_zeros(B, self.hidden)
        outs = []
        for j in range(T):
            h = self._flow(h, dt[:, j : j + 1])
            inp = torch.cat([x[:, j] * m[:, j], m[:, j], ctx[:, j]], dim=-1)
            h = _hold(valid[:, j], self.update(inp, h), h)
            outs.append(h)
        return torch.stack(outs, dim=1)


class NeuralCDE(nn.Module):
    """Neural CDE (Kidger et al. 2020) driven by the piecewise-linear path (time, visit count, forward-filled x)."""

    def __init__(self, hidden: int, n_a: int, n_s: int, substeps: int = 4):
        super().__init__()
        self.hidden, self.substeps = hidden, substeps
        self.channels = 2 + n_a
        self.init = nn.Linear(self.channels + n_s, hidden)
        self.field1 = nn.Linear(hidden, hidden)
        self.field2 = nn.Linear(hidden, hidden * self.channels)

    def _field(self, h):
        return torch.tanh(self.field2(torch.tanh(self.field1(h)))).view(h.shape[0], self.hidden, self.channels)

    def forward(self, x, m, t, s, valid):
        B, T, A = x.shape
        t_abs = t / DAY_SCALE  # same time unit as the other families, so a long gap is a large increment
        ff = x.new_zeros(B, A)
        count = x.new_zeros(B)
        path = []
        for j in range(T):
            mj = m[:, j]
            ff = _hold(valid[:, j], mj * x[:, j] + (1.0 - mj) * ff, ff)
            count = count + valid[:, j] / 10.0
            path.append(torch.cat([t_abs[:, j : j + 1], count.unsqueeze(-1), ff], dim=-1))
        h = torch.tanh(self.init(torch.cat([path[0], s], dim=-1)))
        outs = [h]
        for j in range(1, T):
            dx = (path[j] - path[j - 1]) / self.substeps
            for _ in range(self.substeps):
                h = h + torch.bmm(self._field(h), dx.unsqueeze(-1)).squeeze(-1)
            outs.append(h)
        return torch.stack(outs, dim=1)


class CTTransformer(nn.Module):
    """Causal transformer with a learnable per-head exponential time-distance bias (continuous time)."""

    def __init__(self, hidden: int, n_a: int, n_s: int, heads: Optional[int] = None, layers: int = 2):
        super().__init__()
        self.hidden = hidden
        self.heads = heads or (2 if hidden <= 16 else 4)
        self.dk = hidden // self.heads
        self.embed = nn.Linear(2 * n_a + n_s + 1 + 1, hidden)
        self.qkv = nn.ModuleList([nn.Linear(hidden, 3 * hidden) for _ in range(layers)])
        self.proj = nn.ModuleList([nn.Linear(hidden, hidden) for _ in range(layers)])
        self.ff = nn.ModuleList(
            [nn.Sequential(nn.Linear(hidden, 2 * hidden), nn.GELU(), nn.Linear(2 * hidden, hidden)) for _ in range(layers)]
        )
        self.ln1 = nn.ModuleList([nn.LayerNorm(hidden) for _ in range(layers)])
        self.ln2 = nn.ModuleList([nn.LayerNorm(hidden) for _ in range(layers)])
        self.ln_out = nn.LayerNorm(hidden)
        self.lam = nn.Parameter(torch.full((self.heads,), 0.5))

    def forward(self, x, m, t, s, valid):
        B, T, _ = x.shape
        dt, t_abs = _time_inputs(t, valid)
        h = self.embed(torch.cat([x * m, m, _context(s, t_abs), dt.unsqueeze(-1)], dim=-1))
        gap = (t.unsqueeze(2) - t.unsqueeze(1)).abs() / DAY_SCALE  # [B, T, T]
        idx = torch.arange(T, device=x.device)
        causal = (idx.unsqueeze(1) >= idx.unsqueeze(0)).unsqueeze(0)  # j <= i
        diagonal = (idx.unsqueeze(1) == idx.unsqueeze(0)).unsqueeze(0)
        allowed = (causal & (valid.unsqueeze(1) > 0.5)) | diagonal
        bias = -F.softplus(self.lam).view(1, self.heads, 1, 1) * gap.unsqueeze(1)
        neg = torch.full_like(bias, -1e9)
        for qkv, proj, ff, ln1, ln2 in zip(self.qkv, self.proj, self.ff, self.ln1, self.ln2):
            q, k, v = qkv(ln1(h)).chunk(3, dim=-1)
            q = q.view(B, T, self.heads, self.dk).transpose(1, 2)
            k = k.view(B, T, self.heads, self.dk).transpose(1, 2)
            v = v.view(B, T, self.heads, self.dk).transpose(1, 2)
            score = q @ k.transpose(-1, -2) / math.sqrt(self.dk) + bias
            score = torch.where(allowed.unsqueeze(1), score, neg)
            att = torch.softmax(score, dim=-1) @ v
            h = h + proj(att.transpose(1, 2).reshape(B, T, self.hidden))
            h = h + ff(ln2(h))
        return self.ln_out(h)


class GRUwE(nn.Module):
    """GRUwE (E24): time-triggered exponential decay of the state, then an observation-triggered masked GRU update."""

    def __init__(self, hidden: int, n_a: int, n_s: int):
        super().__init__()
        self.hidden = hidden
        self.decay = nn.Linear(1, hidden)  # gamma(dt) = exp(-max(0, W dt + b))
        d_in = n_a + n_s + 1
        self.w = nn.Linear(d_in, 3 * hidden)
        self.u_zr = nn.Linear(hidden, 2 * hidden, bias=False)
        self.u_h = nn.Linear(hidden, hidden, bias=False)
        self.v = nn.Linear(n_a, 3 * hidden, bias=False)

    def forward(self, x, m, t, s, valid):
        B, T, _ = x.shape
        dt, t_abs = _time_inputs(t, valid)
        ctx = _context(s, t_abs)
        h = x.new_zeros(B, self.hidden)
        outs = []
        for j in range(T):
            g = torch.exp(-F.relu(self.decay(dt[:, j : j + 1]))) * h
            mj = m[:, j]
            wz, wr, wh = self.w(torch.cat([x[:, j] * mj, ctx[:, j]], dim=-1)).chunk(3, dim=-1)
            vz, vr, vh = self.v(mj).chunk(3, dim=-1)
            uz, ur = self.u_zr(g).chunk(2, dim=-1)
            z = torch.sigmoid(wz + uz + vz)
            r = torch.sigmoid(wr + ur + vr)
            cand = torch.tanh(wh + self.u_h(r * g) + vh)
            h = _hold(valid[:, j], (1.0 - z) * g + z * cand, h)
            outs.append(h)
        return torch.stack(outs, dim=1)


class IrregularSSM(nn.Module):
    """Selective diagonal state-space model whose step is scaled by the elapsed time (S4D / Mamba style)."""

    def __init__(self, hidden: int, n_a: int, n_s: int, d_state: int = 8):
        super().__init__()
        self.hidden, self.d_state = hidden, d_state
        self.inp = nn.Linear(2 * n_a + n_s + 1 + 1, 2 * hidden)
        self.dt_proj = nn.Linear(hidden, hidden)
        self.b_proj = nn.Linear(hidden, d_state)
        self.c_proj = nn.Linear(hidden, d_state)
        self.log_a = nn.Parameter(torch.log(torch.arange(1, d_state + 1, dtype=torch.float32)).repeat(hidden, 1))
        self.d_skip = nn.Parameter(torch.ones(hidden))
        self.out = nn.Linear(hidden, hidden)
        self.norm = nn.LayerNorm(hidden)

    def forward(self, x, m, t, s, valid):
        B, T, _ = x.shape
        dt, t_abs = _time_inputs(t, valid)
        u_all, z_all = self.inp(torch.cat([x * m, m, _context(s, t_abs), dt.unsqueeze(-1)], dim=-1)).chunk(2, dim=-1)
        a = -torch.exp(self.log_a)  # [H, N], strictly negative
        state = x.new_zeros(B, self.hidden, self.d_state)
        outs = []
        for j in range(T):
            u = u_all[:, j]
            delta = F.softplus(self.dt_proj(u)) * (1.0 + dt[:, j : j + 1])  # elapsed time lengthens the step
            d_a = torch.exp(delta.unsqueeze(-1) * a)  # [B, H, N]
            d_b = (d_a - 1.0) / a
            new = d_a * state + d_b * self.b_proj(u).unsqueeze(1) * u.unsqueeze(-1)
            state = _hold(valid[:, j], new, state)
            y = (state * self.c_proj(u).unsqueeze(1)).sum(-1) + self.d_skip * u
            outs.append(self.out(y * F.silu(z_all[:, j])))
        return self.norm(torch.stack(outs, dim=1))


_ENCODERS = {
    "grud": GRUD,
    "gru_ode_bayes": GRUODEBayes,
    "neural_cde": NeuralCDE,
    "ct_transformer": CTTransformer,
    "gruwe": GRUwE,
    "ssm": IrregularSSM,
}


class K4Network(nn.Module):
    """Encoder + per-visit risk head (+ a reconstruction head used only for pre-training)."""

    def __init__(self, family: str, hidden: int, n_a: int = N_CHANNELS, n_s: int = N_STATIC):
        super().__init__()
        if family not in _ENCODERS:
            raise ValueError(f"unknown family {family!r}; choose from {FAMILIES}")
        self.family, self.hidden, self.n_a, self.n_s = family, hidden, n_a, n_s
        self.encoder = _ENCODERS[family](hidden, n_a, n_s)
        self.risk_head = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))
        self.recon_head = nn.Linear(hidden, n_a)

    def states(self, x, m, t, s, valid):
        return self.encoder(x, m, t, s, valid.to(x.dtype))

    def forward(self, x, m, t, s, valid):
        """Risk logits [B, T]; the logit at visit j uses only visits <= j."""
        return self.risk_head(self.states(x, m, t, s, valid)).squeeze(-1)

    def reconstruct(self, x, m, t, s, valid):
        return self.recon_head(self.states(x, m, t, s, valid))


def build_network(family: str, size: str = "medium", seed: int = 0) -> K4Network:
    torch.manual_seed(seed)
    return K4Network(family, SIZES[size])


def count_parameters(net: nn.Module) -> int:
    return int(sum(p.numel() for p in net.parameters()))


# ---------------------------------------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------------------------------------
@dataclass
class FitConfig:
    lr: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 32
    max_epochs: int = 120
    patience: int = 12
    clip: float = 1.0
    val_fraction: float = 0.2
    min_val: int = 10


@dataclass
class FitResult:
    network: K4Network
    best_epoch: int
    val_curve: List[float] = field(default_factory=list)
    train_seconds: float = 0.0


def _tensors(ds: SequenceSet, idx: np.ndarray, with_labels: bool = False):
    Tb = max(int(ds.lengths[idx].max()), 1)
    sl = np.s_[idx, :Tb]
    out = [
        torch.from_numpy(ds.x[sl]),
        torch.from_numpy(ds.m[sl]),
        torch.from_numpy(ds.t[sl]),
        torch.from_numpy(ds.s[idx]),
        torch.from_numpy(ds.valid[sl].astype(np.float32)),
    ]
    if with_labels:
        out += [torch.from_numpy(ds.y[sl]), torch.from_numpy(ds.row_mask[sl])]
    return out


def _risk_loss(net: K4Network, ds: SequenceSet, idx: np.ndarray) -> Optional[torch.Tensor]:
    x, m, t, s, v, y, rm = _tensors(ds, idx, with_labels=True)
    if not bool(rm.any()):
        return None
    logits = net(x, m, t, s, v)
    return F.binary_cross_entropy_with_logits(logits[rm], y[rm])


def _train_epochs(net, ds, idx_train, cfg: FitConfig, epochs: int, rng, val=None):
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    best, best_epoch, wait, curve = float("inf"), 0, 0, []
    for epoch in range(1, epochs + 1):
        net.train()
        order = rng.permutation(idx_train)
        for k in range(0, len(order), cfg.batch_size):
            loss = _risk_loss(net, ds, order[k : k + cfg.batch_size])
            if loss is None:
                continue
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), cfg.clip)
            opt.step()
        if val is not None:
            net.eval()
            with torch.no_grad():
                vl = _risk_loss(net, ds, val)
            vl = float("inf") if vl is None else float(vl)
            curve.append(vl)
            if vl < best - 1e-6:
                best, best_epoch, wait = vl, epoch, 0
            else:
                wait += 1
                if wait >= cfg.patience:
                    break
    return best_epoch, curve


def fit_risk_model(
    family: str,
    size: str,
    ds: SequenceSet,
    cfg: FitConfig,
    seed: int,
    encoder_state: Optional[Dict[str, torch.Tensor]] = None,
) -> FitResult:
    """Early-stopped fit on a held-out part of `ds`, then a refit on all of `ds` for the selected epoch count."""
    if ds.y is None or ds.row_mask is None:
        raise ValueError("fit_risk_model needs labels: call attach_labels first")
    t0 = time.time()
    P = len(ds)
    rng = np.random.default_rng(seed)
    order = rng.permutation(P)
    n_val = int(min(max(cfg.min_val, round(cfg.val_fraction * P)), max(P - 2, 1)))
    val_idx, tr_idx = order[:n_val], order[n_val:]

    def fresh() -> K4Network:
        net = build_network(family, size, seed)
        if encoder_state is not None:
            net.encoder.load_state_dict(encoder_state)
        return net

    net = fresh()
    best_epoch, curve = _train_epochs(net, ds, tr_idx, cfg, cfg.max_epochs, np.random.default_rng(seed + 1), val=val_idx)
    best_epoch = max(best_epoch, 1)
    final = fresh()
    _train_epochs(final, ds, np.arange(P), cfg, best_epoch, np.random.default_rng(seed + 2))
    final.eval()
    return FitResult(final, best_epoch, curve, time.time() - t0)


@torch.no_grad()
def predict_probabilities(net: K4Network, ds: SequenceSet, batch: int = 256) -> np.ndarray:
    """Risk probabilities [P, T] (meaningful where `ds.valid`)."""
    net.eval()
    out = np.zeros(ds.valid.shape, dtype=np.float32)
    for k in range(0, len(ds), batch):
        idx = np.arange(k, min(k + batch, len(ds)))
        x, m, t, s, v = _tensors(ds, idx)
        p = torch.sigmoid(net(x, m, t, s, v)).numpy()
        out[idx, : p.shape[1]] = p
    return out


# ---------------------------------------------------------------------------------------------------------
# Masked-analyte pre-training
# ---------------------------------------------------------------------------------------------------------
@dataclass
class PretrainConfig:
    lr: float = 2e-3
    weight_decay: float = 1e-4
    batch_size: int = 64
    epochs: int = 25
    mask_rate: float = 0.25
    val_fraction: float = 0.1
    clip: float = 1.0


@dataclass
class PretrainResult:
    encoder_state: Dict[str, torch.Tensor]
    initial_val_loss: float
    val_losses: List[float]
    train_seconds: float


def _masked_batch(ds: SequenceSet, idx: np.ndarray, rate: float, gen: torch.Generator):
    x, m, t, s, v = _tensors(ds, idx)
    pick = (torch.rand(m.shape, generator=gen) < rate) & (m > 0.5) & (v.unsqueeze(-1) > 0.5)
    pick[..., N_LAB:] = False  # only laboratory values are hidden; symptom grades are covariates
    sel = pick.to(x.dtype)
    return x * (1.0 - sel), m * (1.0 - sel), t, s, v, x, pick


def _recon_loss(net: K4Network, ds: SequenceSet, idx: np.ndarray, rate: float, gen: torch.Generator):
    xi, mi, t, s, v, x_true, pick = _masked_batch(ds, idx, rate, gen)
    if not bool(pick.any()):
        return None
    pred = net.reconstruct(xi, mi, t, s, v)
    return F.huber_loss(pred[pick], x_true[pick], delta=1.0)


def pretrain_encoder(family: str, size: str, corpus: SequenceSet, cfg: PretrainConfig, seed: int) -> PretrainResult:
    """Masked-analyte modelling: hide observed values, predict them from the state at that visit."""
    t0 = time.time()
    net = build_network(family, size, seed)
    P = len(corpus)
    rng = np.random.default_rng(seed)
    order = rng.permutation(P)
    n_val = max(int(round(cfg.val_fraction * P)), 1)
    val_idx, tr_idx = order[:n_val], order[n_val:]

    def val_loss() -> float:
        net.eval()
        gen = torch.Generator().manual_seed(12345)  # a fixed mask, so the curve is comparable across epochs
        tot, n = 0.0, 0
        with torch.no_grad():
            for k in range(0, len(val_idx), 256):
                loss = _recon_loss(net, corpus, val_idx[k : k + 256], cfg.mask_rate, gen)
                if loss is not None:
                    tot += float(loss)
                    n += 1
        return tot / max(n, 1)

    initial = val_loss()
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    gen = torch.Generator().manual_seed(seed + 99)
    curve: List[float] = []
    for _ in range(cfg.epochs):
        net.train()
        perm = rng.permutation(tr_idx)
        for k in range(0, len(perm), cfg.batch_size):
            loss = _recon_loss(net, corpus, perm[k : k + cfg.batch_size], cfg.mask_rate, gen)
            if loss is None:
                continue
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), cfg.clip)
            opt.step()
        curve.append(val_loss())
    state = {k: v.detach().clone() for k, v in net.encoder.state_dict().items()}
    return PretrainResult(state, initial, curve, time.time() - t0)


# ---------------------------------------------------------------------------------------------------------
# Export: safetensors (weights + JSON metadata) and ONNX; no Python-object serialisation.
# ---------------------------------------------------------------------------------------------------------
def save_safetensors(net: K4Network, path: Path, extra: Optional[Dict[str, str]] = None) -> None:
    from safetensors.torch import save_file

    meta = {
        "format": FORMAT,
        "family": net.family,
        "hidden": str(net.hidden),
        "n_analytes": str(net.n_a),
        "n_static": str(net.n_s),
        "analytes": json.dumps(list(ANALYTES)),
        "symptoms": json.dumps(list(SYMPTOMS)),
    }
    meta.update({str(k): str(v) for k, v in (extra or {}).items()})
    save_file({k: v.contiguous() for k, v in net.state_dict().items()}, str(path), metadata=meta)


def load_safetensors(path: Path) -> K4Network:
    from safetensors import safe_open
    from safetensors.torch import load_file

    with safe_open(str(path), framework="pt") as f:
        meta = f.metadata() or {}
    if meta.get("format") != FORMAT:
        raise ValueError(f"not a {FORMAT} file")
    net = K4Network(meta["family"], int(meta["hidden"]), int(meta["n_analytes"]), int(meta["n_static"]))
    net.load_state_dict(load_file(str(path)))
    net.eval()
    return net


class _OnnxWrapper(nn.Module):
    def __init__(self, net: K4Network):
        super().__init__()
        self.net = net

    def forward(self, x, m, t, s, valid):
        return torch.sigmoid(self.net(x, m, t, s, valid))


def export_onnx(net: K4Network, path: Path, max_steps: int = MAX_STEPS) -> None:
    """Export the risk probabilities for padded input of `max_steps` visits (batch size is dynamic)."""
    net.eval()
    B = 2
    dummy = (
        torch.zeros(B, max_steps, net.n_a),
        torch.zeros(B, max_steps, net.n_a),
        torch.zeros(B, max_steps),
        torch.zeros(B, net.n_s),
        torch.ones(B, max_steps),
    )
    torch.onnx.export(
        _OnnxWrapper(net),
        dummy,
        str(path),
        input_names=["x", "m", "t", "s", "valid"],
        output_names=["risk"],
        dynamic_axes={k: {0: "batch"} for k in ("x", "m", "t", "s", "valid", "risk")},
        opset_version=17,
        dynamo=False,
    )


# ---------------------------------------------------------------------------------------------------------
# Cost reporting
# ---------------------------------------------------------------------------------------------------------
@torch.no_grad()
def measure_latency(net: K4Network, steps: int = 8, repeats: int = 200) -> Dict[str, float]:
    """Single-patient CPU forward latency in ms (median and 95th percentile), one thread."""
    net.eval()
    prev = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        x = torch.randn(1, steps, net.n_a)
        m = torch.ones(1, steps, net.n_a)
        t = torch.arange(steps, dtype=torch.float32).unsqueeze(0) * 90.0
        s = torch.zeros(1, net.n_s)
        v = torch.ones(1, steps)
        for _ in range(10):
            net(x, m, t, s, v)
        times = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            net(x, m, t, s, v)
            times.append((time.perf_counter() - t0) * 1000.0)
    finally:
        torch.set_num_threads(prev)
    return {"median_ms": float(np.median(times)), "p95_ms": float(np.percentile(times, 95))}


def state_bytes(net: nn.Module) -> int:
    return int(sum(p.numel() * p.element_size() for p in net.state_dict().values()))


__all__ = [
    "ANALYTES",
    "FAMILIES",
    "N_CHANNELS",
    "N_LAB",
    "SYMPTOMS",
    "SIZES",
    "FitConfig",
    "K4Network",
    "PretrainConfig",
    "SequenceSet",
    "attach_labels",
    "build_network",
    "build_sequences",
    "count_parameters",
    "export_onnx",
    "fit_risk_model",
    "load_safetensors",
    "log_reference",
    "measure_latency",
    "predict_probabilities",
    "pretrain_encoder",
    "save_safetensors",
    "state_bytes",
]
