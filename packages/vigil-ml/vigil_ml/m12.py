"""vigil_ml.m12: FederatedAveraging and DP-SGD for EXP-M12-001.

Specification: experiments/EXP-M12-001/PREREG.md (committed before this file).
This module never imports the simulator and never reads patient rows. The only values that
cross the client/server boundary are masked weight arrays and the integers n_k.
Research code on synthetic data. (ε, δ)-DP is a bound on a mechanism, not a legal clearance.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np

HIDDEN = 32
LR = 0.05
BATCH = 32
CLIP_C = 1.0
NOISE_MULT = 1.0
ROUNDS = 20
LOCAL_EPOCHS_FED = 2
EPOCHS_SOLO = 4


def init_mlp(d_in: int, rng: np.random.Generator, hidden: int = HIDDEN) -> list[np.ndarray]:
    """Xavier/Kaiming Gaussian init; float32. Same rng → same weights."""
    w1 = (rng.standard_normal((hidden, d_in)).astype(np.float32) * np.float32(math.sqrt(2.0 / d_in)))
    b1 = np.zeros(hidden, dtype=np.float32)
    w2 = (rng.standard_normal((1, hidden)).astype(np.float32) * np.float32(math.sqrt(2.0 / hidden)))
    b2 = np.zeros(1, dtype=np.float32)
    return [w1, b1, w2, b2]


def clone_weights(weights: Sequence[np.ndarray]) -> list[np.ndarray]:
    return [np.array(w, dtype=np.float32, copy=True) for w in weights]


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-z))


def logits(weights: Sequence[np.ndarray], x: np.ndarray) -> np.ndarray:
    w1, b1, w2, b2 = weights
    hidden = np.maximum(x @ w1.T + b1, 0.0)
    return (hidden @ w2.T + b2).ravel()


def predict_proba(weights: Sequence[np.ndarray], x: np.ndarray) -> np.ndarray:
    return _sigmoid(logits(weights, x)).astype(np.float32)


def _forward(weights: Sequence[np.ndarray], x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    w1, b1, w2, _b2 = weights
    pre = x @ w1.T + b1
    post = np.maximum(pre, 0.0)
    z = (post @ w2.T + weights[3]).ravel()
    return z, pre, post


def _example_grads(
    weights: Sequence[np.ndarray], x: np.ndarray, y: np.ndarray
) -> list[np.ndarray]:
    """Per-row gradients of mean-unreduced BCE-with-logits. x is (L, d), y is (L,)."""
    w2 = weights[2]
    z, pre, post = _forward(weights, x)
    d_z = (_sigmoid(z) - y).astype(np.float32)
    d_w2 = d_z[:, None] * post
    d_b2 = d_z[:, None]
    d_post = d_z[:, None] * w2
    d_pre = d_post * (pre > 0.0).astype(np.float32)
    d_w1 = d_pre[:, :, None] * x[:, None, :]
    d_b1 = d_pre
    return [d_w1, d_b1, d_w2, d_b2]


def clip_per_example(grads: Sequence[np.ndarray], clip_c: float) -> list[np.ndarray]:
    """Clip each row's concatenated gradient to ℓ2 norm clip_c (PREREG: C = 1.0)."""
    lot = int(grads[0].shape[0])
    sq = np.zeros(lot, dtype=np.float64)
    flats = []
    for g in grads:
        flat = g.reshape(lot, -1)
        flats.append(flat)
        sq += np.sum(np.square(flat.astype(np.float64)), axis=1)
    nrm = np.sqrt(sq)
    scale = np.maximum(nrm / float(clip_c), 1.0).astype(np.float32)
    out: list[np.ndarray] = []
    for g, flat in zip(grads, flats):
        clipped = (flat / scale[:, None]).reshape(g.shape).astype(np.float32)
        out.append(clipped)
    return out


def clip_one(grad_tensors: Sequence[np.ndarray], clip_c: float) -> list[np.ndarray]:
    """Clip a single-example gradient (no leading lot axis) to ℓ2 norm clip_c."""
    sq = 0.0
    for g in grad_tensors:
        sq += float(np.sum(np.square(g.astype(np.float64))))
    nrm = math.sqrt(sq)
    scale = max(nrm / float(clip_c), 1.0)
    return [(g / np.float32(scale)).astype(np.float32) for g in grad_tensors]


def _mean_tensors(grads: Sequence[np.ndarray]) -> list[np.ndarray]:
    return [np.mean(g, axis=0).astype(np.float32) for g in grads]


def _sgd_apply(weights: list[np.ndarray], grads: Sequence[np.ndarray], lr: float) -> None:
    for w, g in zip(weights, grads):
        w -= np.float32(lr) * g


def train_sgd(
    weights: list[np.ndarray],
    x: np.ndarray,
    y: np.ndarray,
    epochs: int,
    batch: int,
    lr: float,
    rng: np.random.Generator,
) -> list[np.ndarray]:
    """Non-private SGD. Mutates a clone and returns it."""
    w = clone_weights(weights)
    n = int(x.shape[0])
    if n == 0:
        return w
    batch = max(1, min(int(batch), n))
    for _ in range(int(epochs)):
        order = rng.permutation(n)
        for start in range(0, n, batch):
            idx = order[start : start + batch]
            xb = x[idx]
            yb = y[idx]
            mean_g = _mean_tensors(_example_grads(w, xb, yb))
            _sgd_apply(w, mean_g, lr)
    return w


def train_dp_sgd(
    weights: list[np.ndarray],
    x: np.ndarray,
    y: np.ndarray,
    epochs: int,
    lot: int,
    lr: float,
    clip_c: float,
    sigma: float,
    rng: np.random.Generator,
    max_steps: Optional[int] = None,
) -> tuple[list[np.ndarray], int]:
    """DP-SGD (Abadi et al. Algorithm 1). Noise std on the average is σ C / L."""
    w = clone_weights(weights)
    n = int(x.shape[0])
    if n == 0:
        return w, 0
    lot = max(1, min(int(lot), n))
    steps = 0
    n_epochs = 10**9 if max_steps is not None else int(epochs)
    for _ in range(n_epochs):
        order = rng.permutation(n)
        for start in range(0, n, lot):
            idx = order[start : start + lot]
            xb = x[idx]
            yb = y[idx]
            L = int(xb.shape[0])
            clipped = clip_per_example(_example_grads(w, xb, yb), clip_c)
            mean_g = _mean_tensors(clipped)
            noise_std = float(sigma) * float(clip_c) / float(L)
            noisy = [
                g + rng.normal(0.0, noise_std, size=g.shape).astype(np.float32) for g in mean_g
            ]
            _sgd_apply(w, noisy, lr)
            steps += 1
            if max_steps is not None and steps >= max_steps:
                return w, steps
    return w, steps


def make_pairwise_masks(
    counts: Sequence[int],
    shapes: Sequence[tuple[int, ...]],
    rng: np.random.Generator,
) -> list[list[np.ndarray]]:
    """Pairwise masks with n-weighted cancellation: Σ_k n_k mask_k = 0."""
    k = len(counts)
    masks = [[np.zeros(s, dtype=np.float32) for s in shapes] for _ in range(k)]
    for i in range(k):
        for j in range(i + 1, k):
            for layer, shape in enumerate(shapes):
                m = rng.normal(0.0, 1.0, size=shape).astype(np.float32)
                masks[i][layer] = masks[i][layer] + (m / float(counts[i]))
                masks[j][layer] = masks[j][layer] - (m / float(counts[j]))
    return masks


def apply_masks(
    client_weights: Sequence[Sequence[np.ndarray]],
    masks: Sequence[Sequence[np.ndarray]],
) -> list[list[np.ndarray]]:
    out: list[list[np.ndarray]] = []
    for ws, ms in zip(client_weights, masks):
        out.append([w + m for w, m in zip(ws, ms)])
    return out


def server_aggregate(
    masked_weights: list[list[np.ndarray]],
    counts: list[int],
) -> list[np.ndarray]:
    """n-weighted mean of masked client weight arrays (FedAvg)."""
    total = float(sum(counts))
    n_parts = len(masked_weights[0])
    acc = [np.zeros_like(masked_weights[0][i]) for i in range(n_parts)]
    for client, n in zip(masked_weights, counts):
        share = n / total
        for i in range(n_parts):
            acc[i] = acc[i] + share * client[i]
    return acc


def weighted_mask_sum(
    masks: Sequence[Sequence[np.ndarray]], counts: Sequence[int]
) -> list[np.ndarray]:
    n_parts = len(masks[0])
    acc = [np.zeros_like(masks[0][i]) for i in range(n_parts)]
    for ms, n in zip(masks, counts):
        for i in range(n_parts):
            acc[i] = acc[i] + float(n) * ms[i]
    return acc


def fedavg_train(
    site_x: Sequence[np.ndarray],
    site_y: Sequence[np.ndarray],
    init: Sequence[np.ndarray],
    rounds: int,
    local_epochs: int,
    batch: int,
    lr: float,
    rng_sgd: np.random.Generator,
    rng_mask: np.random.Generator,
    dp: Optional[tuple[float, float, np.random.Generator]] = None,
) -> tuple[list[np.ndarray], list[int]]:
    """In-process FedAvg. dp is (clip_c, sigma, rng) or None.

    Returns (server weights, per-site DP-SGD step counts). Step counts are 0 when dp is None.
    """
    counts = [int(x.shape[0]) for x in site_x]
    server = clone_weights(init)
    dp_steps = [0] * len(site_x)
    shapes = [tuple(w.shape) for w in server]
    for _ in range(int(rounds)):
        client_ws: list[list[np.ndarray]] = []
        for k, (x, y) in enumerate(zip(site_x, site_y)):
            if dp is None:
                wk = train_sgd(server, x, y, local_epochs, batch, lr, rng_sgd)
            else:
                clip_c, sigma, rng_dp = dp
                lot = min(BATCH, max(1, counts[k]))
                wk, steps = train_dp_sgd(
                    server, x, y, local_epochs, lot, lr, clip_c, sigma, rng_dp
                )
                dp_steps[k] += steps
            client_ws.append(wk)
        masks = make_pairwise_masks(counts, shapes, rng_mask)
        masked = apply_masks(client_ws, masks)
        server = server_aggregate(masked, counts)
    return server, dp_steps


def _log_add(a: float, b: float) -> float:
    if a == -math.inf:
        return b
    if b == -math.inf:
        return a
    m = max(a, b)
    return m + math.log1p(math.exp(-abs(a - b)))


def sampled_gaussian_rdp(q: float, sigma: float, alpha: int) -> float:
    """RDP of the sampled Gaussian mechanism at integer order alpha (moments accountant)."""
    if q <= 0.0:
        return 0.0
    if q >= 1.0:
        return float(alpha) / (2.0 * sigma * sigma)
    log_a = -math.inf
    log_q = math.log(q)
    log_1q = math.log1p(-q)
    sig2 = sigma * sigma
    for i in range(alpha + 1):
        log_coef = math.log(math.comb(alpha, i)) + i * log_q + (alpha - i) * log_1q
        s = log_coef + (i * i - i) / (2.0 * sig2)
        log_a = _log_add(log_a, s)
    return log_a / (alpha - 1)


def moments_epsilon(
    q: float,
    sigma: float,
    steps: int,
    delta: float,
    max_order: int = 64,
) -> float:
    """Convert accumulated sampled-Gaussian RDP to (ε, δ)-DP. Equivalent to Abadi's accountant."""
    if steps <= 0:
        return 0.0
    best = math.inf
    for alpha in range(2, int(max_order) + 1):
        rdp = sampled_gaussian_rdp(q, sigma, alpha) * float(steps)
        eps = rdp + math.log(1.0 / delta) / (alpha - 1)
        if eps < best:
            best = eps
    return float(best)


def privacy_ledger_row(
    n_k: int,
    steps: int,
    sigma: float = NOISE_MULT,
    clip_c: float = CLIP_C,
    delta: float = 1.0 / 910.0,
) -> dict:
    lot = min(BATCH, max(1, int(n_k)))
    q = lot / float(max(1, n_k))
    return {
        "eps": moments_epsilon(q, sigma, steps, delta),
        "delta": float(delta),
        "sigma": float(sigma),
        "C": float(clip_c),
        "steps": int(steps),
        "q": float(q),
        "n_k": int(n_k),
        "lot": int(lot),
    }
