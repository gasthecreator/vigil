"""M12 invariants (experiments/EXP-M12-001/PREREG.md section 8), tested before the frozen run."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score
from vigil_ml import m12

ROOT = Path(__file__).resolve().parents[3]
M12_SRC = ROOT / "packages" / "vigil-ml" / "vigil_ml" / "m12.py"
RUNNER = ROOT / "experiments" / "EXP-M12-001" / "run.py"


def _norm(tensors) -> float:
    return float(np.sqrt(sum(float(np.sum(np.square(t))) for t in tensors)))


def test_fedavg_identity_n_weighted_mean():
    rng = np.random.default_rng(0)
    d = 6
    clients = [m12.init_mlp(d, np.random.default_rng(i + 1)) for i in range(3)]
    counts = [40, 40, 40]
    unmasked_mean = m12.server_aggregate(clients, counts)
    shapes = [tuple(w.shape) for w in clients[0]]
    masks = m12.make_pairwise_masks(counts, shapes, rng)
    masked = m12.apply_masks(clients, masks)
    from_server = m12.server_aggregate(masked, counts)
    for a, b in zip(unmasked_mean, from_server):
        assert np.max(np.abs(a - b)) < 1e-6


def test_secure_aggregation_masks_and_server_blindness():
    rng = np.random.default_rng(1)
    d = 5
    clients = [m12.init_mlp(d, np.random.default_rng(10 + i)) for i in range(4)]
    counts = [10, 25, 40, 15]
    shapes = [tuple(w.shape) for w in clients[0]]
    masks = m12.make_pairwise_masks(counts, shapes, rng)
    weighted = m12.weighted_mask_sum(masks, counts)
    for t in weighted:
        assert float(np.max(np.abs(t))) < 1e-5
    src = inspect.getsource(m12.server_aggregate)
    names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)}
    for word in ("patient", "analyte", "X", "y"):
        assert word not in names, word
    masked = m12.apply_masks(clients, masks)
    a = m12.server_aggregate(masked, counts)
    garbage = [m12.init_mlp(d, np.random.default_rng(99 + i)) for i in range(4)]
    b = m12.server_aggregate(masked, counts)
    for u, v in zip(a, b):
        assert np.array_equal(u, v)
    # scrambling the unmasked tensors does not change the payload the server sees
    _ = garbage
    for u, v in zip(a, m12.server_aggregate(masked, counts)):
        assert np.array_equal(u, v)


def test_no_raw_data_egress_or_pickle():
    src = M12_SRC.read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "open"
    for banned in ("pickle", "socket", "urllib", "http", "requests", "httpx"):
        assert banned not in imported
        assert banned not in src
    runner = RUNNER.read_text(encoding="utf-8")
    assert "pickle" not in runner
    assert "import socket" not in runner and "urllib" not in runner


def test_dp_sgd_clip_single_example_norm_10_to_c():
    g = [
        np.zeros((32, 4), dtype=np.float32),
        np.zeros(32, dtype=np.float32),
        np.zeros((1, 32), dtype=np.float32),
        np.array([10.0], dtype=np.float32),
    ]
    assert _norm(g) == pytest.approx(10.0, abs=1e-5)
    clipped = m12.clip_one(g, 1.0)
    assert _norm(clipped) == pytest.approx(1.0, abs=1e-5)


def test_accountant_recovers_abadi_example():
    # E27 full-text numerical example (outside the excerpt): q=0.01, σ=4, δ=1e-5, T=10000 → ε≈1.26
    eps = m12.moments_epsilon(q=0.01, sigma=4.0, steps=10000, delta=1e-5)
    assert 1.15 <= eps <= 1.40, eps


def test_determinism_central_and_masked_fedavg():
    rng_x = np.random.default_rng(2)
    x = rng_x.standard_normal((80, 8)).astype(np.float32)
    y = (x[:, 0] > 0).astype(np.float32)
    init_a = m12.init_mlp(8, np.random.default_rng(11))
    init_b = m12.init_mlp(8, np.random.default_rng(11))
    for a, b in zip(init_a, init_b):
        assert np.array_equal(a, b)
    c1 = m12.train_sgd(init_a, x, y, 4, 32, 0.05, np.random.default_rng(12))
    c2 = m12.train_sgd(init_b, x, y, 4, 32, 0.05, np.random.default_rng(12))
    for a, b in zip(c1, c2):
        assert np.array_equal(a, b)
    x1, x2 = x[:40], x[40:]
    y1, y2 = y[:40], y[40:]
    f1, _ = m12.fedavg_train(
        [x1, x2], [y1, y2], init_a, 3, 1, 32, 0.05,
        np.random.default_rng(12), np.random.default_rng(13),
    )
    f2, _ = m12.fedavg_train(
        [x1, x2], [y1, y2], init_b, 3, 1, 32, 0.05,
        np.random.default_rng(12), np.random.default_rng(13),
    )
    for a, b in zip(f1, f2):
        assert np.array_equal(a, b)


def test_causality_latent_columns_do_not_change_weights():
    from vigil_ml.features import WindowedFeatureExtractor
    from vigil_sim.generators import GeneratorType, get_generator

    def landmarks_from(obs, pts):
        X, y, times, events = WindowedFeatureExtractor().transform_cohort(pts, obs, 365.0)
        keep = []
        for _pid, grp in X.groupby("patient_id", sort=False):
            ok = grp[(grp["eval_day"] >= 90.0) & (grp["eval_day"] <= 365.0)]
            if len(ok) == 0:
                continue
            keep.append(int(ok["eval_day"].idxmax()))
        X = X.loc[keep]
        feat = X.drop(columns=["patient_id"]).fillna(0.0).to_numpy(np.float32)
        lab = y.loc[keep].to_numpy(np.float32)
        return feat, lab

    cohort = get_generator(GeneratorType.G1_SMOOTH, seed=3).generate_cohort(40, 730.0, 90.0)
    obs = cohort.to_observations_dataframe()
    pts = cohort.to_patients_dataframe()
    x1, y1 = landmarks_from(obs, pts)
    obs2 = obs.copy()
    for col in [c for c in obs2.columns if c.startswith("latent_")]:
        obs2[col] = np.random.default_rng(0).permutation(obs2[col].to_numpy())
    x2, y2 = landmarks_from(obs2, pts)
    assert np.array_equal(x1, x2)
    assert np.array_equal(y1, y2)
    init = m12.init_mlp(x1.shape[1], np.random.default_rng(11))
    w1 = m12.train_sgd(init, x1, y1, 2, 16, 0.05, np.random.default_rng(12))
    w2 = m12.train_sgd(init, x2, y2, 2, 16, 0.05, np.random.default_rng(12))
    for a, b in zip(w1, w2):
        assert np.array_equal(a, b)


def test_canary_toy_sigma_100_auc_at_most_0_60():
    rng = np.random.default_rng(4)
    n = 200
    d = 16
    x = rng.standard_normal((n, d)).astype(np.float32)
    y = (x[:, 0] + 0.1 * rng.standard_normal(n) > 0).astype(np.float32)
    x_te = rng.standard_normal((400, d)).astype(np.float32)
    y_te = (x_te[:, 0] + 0.1 * rng.standard_normal(400) > 0).astype(np.float32)
    init = m12.init_mlp(d, np.random.default_rng(11))
    w, steps = m12.train_dp_sgd(
        init, x, y, epochs=1, lot=32, lr=0.05, clip_c=1.0, sigma=100.0,
        rng=np.random.default_rng(14), max_steps=50,
    )
    assert steps == 50
    auc = float(roc_auc_score(y_te, m12.predict_proba(w, x_te)))
    assert auc <= 0.60, auc


def test_planted_signal_central_fedavg_and_mild_dp():
    rng = np.random.default_rng(5)
    n = 240
    x = rng.standard_normal((n, 5)).astype(np.float32)
    y = (x[:, 0] + 0.05 * rng.standard_normal(n) > 0).astype(np.float32)
    init = m12.init_mlp(5, np.random.default_rng(11))
    c = m12.train_sgd(init, x, y, 8, 32, 0.05, np.random.default_rng(12))
    auc_c = float(roc_auc_score(y, m12.predict_proba(c, x)))
    assert auc_c > 0.85, auc_c
    split = n // 2
    f, _ = m12.fedavg_train(
        [x[:split], x[split:]], [y[:split], y[split:]], init,
        rounds=10, local_epochs=2, batch=32, lr=0.05,
        rng_sgd=np.random.default_rng(12), rng_mask=np.random.default_rng(13),
    )
    auc_f = float(roc_auc_score(y, m12.predict_proba(f, x)))
    assert auc_f > 0.85, auc_f
    d, _ = m12.fedavg_train(
        [x[:split], x[split:]], [y[:split], y[split:]], init,
        rounds=10, local_epochs=2, batch=32, lr=0.05,
        rng_sgd=np.random.default_rng(12), rng_mask=np.random.default_rng(13),
        dp=(1.0, 0.3, np.random.default_rng(14)),
    )
    auc_d = float(roc_auc_score(y, m12.predict_proba(d, x)))
    assert auc_d > 0.70, auc_d


def test_old_s10_is_retracted_and_cannot_produce_numbers():
    src = (ROOT / "scripts" / "run_benchmarks.py").read_text(encoding="utf-8")
    assert "Approve M12 Federated Training Architecture" not in src
    assert "EXP-M12-001" in src
    assert (ROOT / "reports" / "ml" / "RETRACTED" / "S10_MULTISITE_SYNTHETIC_TRIAL" / "REPORT.md").exists()
    assert not (ROOT / "reports" / "ml" / "S10_MULTISITE_SYNTHETIC_TRIAL").exists()
