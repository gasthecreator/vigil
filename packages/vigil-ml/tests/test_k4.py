"""K4 invariants (experiments/EXP-K4-001/PREREG.md section 8), tested before any study run."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest
import torch
from vigil_ml import k4

ROOT = Path(__file__).resolve().parents[3]
FAMILIES = list(k4.FAMILIES)
A, S = k4.N_CHANNELS, k4.N_STATIC


@pytest.fixture(autouse=True)
def _one_thread():
    prev = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(prev)


def random_batch(B=4, T=8, seed=0, n_real=None):
    g = np.random.default_rng(seed)
    x = g.normal(0, 1, (B, T, A)).astype(np.float32)
    m = (g.random((B, T, A)) < 0.7).astype(np.float32)
    gaps = g.uniform(20, 200, (B, T)).astype(np.float32)
    gaps[:, 0] = 0
    t = np.cumsum(gaps, axis=1).astype(np.float32)
    s = g.normal(0, 1, (B, S)).astype(np.float32)
    valid = np.ones((B, T), dtype=np.float32)
    return [torch.from_numpy(a) for a in (x * m, m, t, s, valid)]


def net_for(family, size="small", seed=0):
    net = k4.build_network(family, size, seed)
    net.eval()
    return net


@pytest.mark.parametrize("family", FAMILIES)
def test_causality_later_visits_never_change_earlier_outputs(family):
    net = net_for(family)
    x, m, t, s, v = random_batch()
    base = net(x, m, t, s, v).detach()
    k = 3
    x2, m2, t2 = x.clone(), m.clone(), t.clone()
    g = torch.Generator().manual_seed(1)
    x2[:, k + 1 :] = torch.randn(x2[:, k + 1 :].shape, generator=g) * 3
    m2[:, k + 1 :] = 1.0 - m2[:, k + 1 :]
    t2[:, k + 1 :] = t2[:, k + 1 :] + 500.0
    changed = net(x2 * m2, m2, t2, s, v).detach()
    assert torch.allclose(base[:, : k + 1], changed[:, : k + 1], atol=1e-6)
    assert not torch.allclose(base[:, k + 1 :], changed[:, k + 1 :], atol=1e-6)  # the later steps do react


@pytest.mark.parametrize("family", FAMILIES)
def test_padding_does_not_change_real_steps(family):
    net = net_for(family)
    x, m, t, s, v = random_batch(T=6)
    base = net(x, m, t, s, v).detach()
    pad = 5
    xp = torch.cat([x, torch.zeros(4, pad, A)], 1)
    mp = torch.cat([m, torch.zeros(4, pad, A)], 1)
    tp = torch.cat([t, t[:, -1:].expand(-1, pad)], 1)
    vp = torch.cat([v, torch.zeros(4, pad)], 1)
    padded = net(xp, mp, tp, s, vp).detach()
    assert torch.allclose(base, padded[:, :6], atol=1e-5)


@pytest.mark.parametrize("family", FAMILIES)
def test_values_under_a_zero_mask_have_no_influence(family):
    net = net_for(family)
    x, m, t, s, v = random_batch()
    clean = net(x * m, m, t, s, v).detach()
    junk = x * m + (1.0 - m) * 37.5
    assert torch.allclose(clean, net(junk, m, t, s, v).detach(), atol=1e-6)


def planted(n, seed, shuffle=0):
    """Label at visit j: the last observed value of analyte 0 (carried forward) plus a long-gap bonus is high."""
    g = np.random.default_rng(seed)
    T = 7
    x = g.normal(0, 1, (n, T, A)).astype(np.float32)
    m = (g.random((n, T, A)) < 0.75).astype(np.float32)
    gaps = g.choice([30.0, 60.0, 200.0], size=(n, T)).astype(np.float32)
    gaps[:, 0] = 0
    t = np.cumsum(gaps, axis=1).astype(np.float32)
    ff = np.zeros(n, dtype=np.float32)
    y = np.zeros((n, T), dtype=np.float32)
    for j in range(T):
        ff = np.where(m[:, j, 0] > 0, x[:, j, 0], ff)
        y[:, j] = ((ff + 0.8 * (gaps[:, j] > 150)) > 0.5).astype(np.float32)
    if shuffle:  # a positive integer selects the permutation of the labels among all rows
        y = y.ravel()[np.random.default_rng(10_000 + shuffle).permutation(y.size)].reshape(y.shape)
    ds = k4.SequenceSet(
        [f"p{i}" for i in range(n)], x * m, m, t, g.normal(0, 1, (n, S)).astype(np.float32),
        np.ones((n, T), dtype=bool), y, np.ones((n, T), dtype=bool),
    )
    return ds


def auc(y, p):
    order = np.argsort(p)
    ranks = np.empty(len(p))
    ranks[order] = np.arange(1, len(p) + 1)
    pos = y == 1
    return (ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * (~pos).sum())


@pytest.mark.parametrize("family", FAMILIES)
def test_each_family_learns_a_planted_signal_and_not_shuffled_labels(family):
    train, test = planted(1000, 1), planted(300, 2)
    cfg = k4.FitConfig(lr=3e-3, max_epochs=40, patience=8)
    res = k4.fit_risk_model(family, "small", train, cfg, seed=0)
    p = k4.predict_probabilities(res.network, test)
    assert auc(test.y.ravel(), p.ravel()) > 0.9
    # A network fitted to shuffled labels is a near-arbitrary function of the inputs: one fit scatters by about 0.1 AUC
    # (see the canary in the study), so the criterion is the mean over five fixed shuffles.
    scores = []
    for k in range(1, 6):
        r0 = k4.fit_risk_model(family, "small", planted(1000, 1, shuffle=k), cfg, seed=k)
        scores.append(auc(test.y.ravel(), k4.predict_probabilities(r0.network, test).ravel()))
    assert float(np.mean(scores)) < 0.6, scores


def correlated_corpus(n, seed):
    """Analytes share a patient-level latent, so a hidden analyte is predictable from the others."""
    g = np.random.default_rng(seed)
    T = 6
    latent = g.normal(0, 1, (n, T, 1))
    x = (latent + 0.3 * g.normal(0, 1, (n, T, A))).astype(np.float32)
    m = (g.random((n, T, A)) < 0.8).astype(np.float32)
    gaps = g.uniform(30, 150, (n, T)).astype(np.float32)
    gaps[:, 0] = 0
    return k4.SequenceSet(
        [f"c{i}" for i in range(n)], x * m, m, np.cumsum(gaps, 1).astype(np.float32),
        np.zeros((n, S), dtype=np.float32), np.ones((n, T), dtype=bool),
    )


@pytest.mark.parametrize("family", FAMILIES)
def test_pretraining_lowers_the_heldout_masked_loss(family):
    res = k4.pretrain_encoder(family, "small", correlated_corpus(160, 3), k4.PretrainConfig(epochs=10, lr=3e-3), seed=0)
    assert res.val_losses[-1] < 0.9 * res.initial_val_loss


@pytest.mark.parametrize("family", FAMILIES)
def test_safetensors_round_trip_and_onnx_parity(family, tmp_path):
    ort = pytest.importorskip("onnxruntime")
    net = net_for(family, "small", seed=4)
    path = tmp_path / "k4.safetensors"
    k4.save_safetensors(net, path, extra={"study": "test"})
    back = k4.load_safetensors(path)
    assert back.family == family
    T = k4.MAX_STEPS
    for B, n_real in ((3, 9), (1, 4)):
        x, m, t, s, v = random_batch(B=B, T=T, seed=B)
        v[:, n_real:] = 0
        t[:, n_real:] = t[:, n_real - 1 : n_real]
        m[:, n_real:] = 0
        x = x * m
        ref = torch.sigmoid(net(x, m, t, s, v)).detach().numpy()
        assert np.array_equal(torch.sigmoid(back(x, m, t, s, v)).detach().numpy(), ref)
        onnx_path = tmp_path / "k4.onnx"
        if not onnx_path.exists():
            k4.export_onnx(net, onnx_path)
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        out = sess.run(["risk"], {"x": x.numpy(), "m": m.numpy(), "t": t.numpy(), "s": s.numpy(), "valid": v.numpy()})[0]
        assert np.max(np.abs(out[:, :n_real] - ref[:, :n_real])) < 1e-4


def test_fit_is_deterministic_for_a_fixed_seed():
    train, test = planted(120, 5), planted(60, 6)
    cfg = k4.FitConfig(lr=3e-3, max_epochs=6, patience=3)
    a = k4.predict_probabilities(k4.fit_risk_model("grud", "small", train, cfg, seed=7).network, test)
    b = k4.predict_probabilities(k4.fit_risk_model("grud", "small", train, cfg, seed=7).network, test)
    assert np.array_equal(a, b)


def _string_constants(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_no_pickle_and_no_forbidden_columns_in_module_or_runner():
    src = (ROOT / "packages" / "vigil-ml" / "vigil_ml" / "k4.py").read_text(encoding="utf-8")
    for bad in ("pickle", "torch.save", "torch.load", "joblib", "dill"):
        assert bad not in src, bad
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "vigil_sim" not in imported
    for rel in ("packages/vigil-ml/vigil_ml/k4.py", "experiments/EXP-K4-001/run.py"):
        p = ROOT / rel
        if not p.exists():
            continue
        for c in _string_constants(p):
            assert not c.startswith(("latent_", "observed_")), (rel, c)


def test_build_sequences_never_truncates_and_log_reference_is_fixed():
    ref = np.ones(k4.N_LAB)
    values = np.full((2, A), np.e)
    ok = k4.build_sequences(["a"], [[0.0, 10.0]], [values], np.zeros((1, S)), ref)
    assert ok.x[0, 0, 0] == pytest.approx(1.0)
    assert ok.x[0, 0, k4.N_LAB] == pytest.approx(np.e)
    assert ok.valid[0].sum() == 2 and ok.t[0, 5] == 10.0
    with pytest.raises(ValueError):
        k4.build_sequences(["a"], [list(range(25))], [np.ones((25, A))], np.zeros((1, S)), ref)
    nan = np.full((1, A), np.nan)
    one = k4.build_sequences(["a"], [[0.0]], [nan], np.zeros((1, S)), ref)
    assert one.m.sum() == 0 and one.x.sum() == 0
    assert k4.log_reference(np.array([1e9]), np.array([1.0]))[0] == 5.0


@pytest.mark.parametrize(
    ("days", "values", "statics", "reference_mid", "max_steps", "message"),
    [
        ([[0.0, 0.0]], [np.ones((2, A))], np.zeros((1, S)), np.ones(k4.N_LAB), 24, "unique"),
        ([[0.0, np.inf]], [np.ones((2, A))], np.zeros((1, S)), np.ones(k4.N_LAB), 24, "finite"),
        ([[0.0]], [np.ones((1, A - 1))], np.zeros((1, S)), np.ones(k4.N_LAB), 24, "shape"),
        ([[0.0]], [np.zeros((1, A))], np.zeros((1, S)), np.ones(k4.N_LAB), 24, "positive"),
        ([[0.0]], [np.ones((1, A))], np.zeros((1, S - 1)), np.ones(k4.N_LAB), 24, "statics"),
        ([[0.0]], [np.ones((1, A))], np.zeros((1, S)), np.zeros(k4.N_LAB), 24, "reference_mid"),
        ([[0.0]], [np.ones((1, A))], np.zeros((1, S)), np.ones(k4.N_LAB), True, "max_steps"),
    ],
)
def test_build_sequences_rejects_malformed_inputs(days, values, statics, reference_mid, max_steps, message):
    with pytest.raises(ValueError, match=message):
        k4.build_sequences(["a"], days, values, statics, reference_mid, max_steps=max_steps)


def test_sequence_set_rejects_nonbinary_masks_and_hidden_values():
    x = np.zeros((1, 2, A), dtype=np.float32)
    m = np.zeros_like(x)
    t = np.array([[0.0, 1.0]], dtype=np.float32)
    s = np.zeros((1, S), dtype=np.float32)
    valid = np.ones((1, 2), dtype=bool)
    with pytest.raises(ValueError, match="m must contain"):
        k4.SequenceSet(["a"], x, m + 0.5, t, s, valid)
    x[0, 0, 0] = 1.0
    with pytest.raises(ValueError, match="unobserved"):
        k4.SequenceSet(["a"], x, m, t, s, valid)


def test_attach_labels_marks_only_rows_that_exist():
    ds = k4.build_sequences(["a", "b"], [[0.0, 5.0], [0.0]], [np.ones((2, A)), np.ones((1, A))], np.zeros((2, S)), np.ones(k4.N_LAB))
    lab = k4.attach_labels(ds, {("a", 5.0): 1.0, ("b", 0.0): 0.0})
    assert lab.row_mask[0].tolist()[:2] == [False, True] and lab.row_mask[1, 0] and lab.y[0, 1] == 1.0
    for invalid in ({("unknown", 0.0): 1.0}, {("a", 1.0): 0.0}, {("a", 5.0): 0.5}, {("a", 5.0): True}):
        with pytest.raises(ValueError):
            k4.attach_labels(ds, invalid)


def test_symptom_channels_are_used_as_given_and_never_masked_for_pretraining():
    n_lab = k4.N_LAB
    ref = np.ones(n_lab)
    vals = np.zeros((2, A))
    vals[:, :n_lab] = np.e
    vals[:, n_lab:] = 0.5
    ds = k4.build_sequences(["a"], [[0.0, 10.0]], [vals], np.zeros((1, S)), ref)
    assert ds.x[0, 0, 0] == pytest.approx(1.0) and ds.x[0, 0, n_lab] == pytest.approx(0.5)
    assert ds.m[0, 0, n_lab:].min() == 1.0
    import torch as _t
    from vigil_ml.k4 import _masked_batch

    xi, mi, _, _, _, x_true, pick = _masked_batch(ds, np.array([0]), 1.0, _t.Generator().manual_seed(0))
    assert bool(pick[..., :n_lab][0, :2].all()) and not bool(pick[..., n_lab:].any())
    assert float(mi[0, 0, n_lab:].min()) == 1.0 and float(xi[0, 0, n_lab]) == pytest.approx(0.5)


def test_the_old_k4_stub_is_retired_and_no_benchmark_scores_it():
    import importlib.util
    import json

    import vigil_ml

    assert importlib.util.find_spec("vigil_ml.deep_zoo_k4") is None
    for name in ("DeepZooK4", "GRUDModel", "ContinuousTimeTransformer", "NeuralCDEModel"):
        assert not hasattr(vigil_ml, name), name
    for rel in ("reports/ml/S9_CROSS_GENERATOR/results.json", "reports/ml/results.json"):
        assert "K4_DeepZoo" not in (ROOT / rel).read_text(encoding="utf-8"), rel
    assert "DeepZooK4" not in (ROOT / "scripts" / "run_benchmarks.py").read_text(encoding="utf-8")
    assert json.loads((ROOT / "reports" / "ml" / "S9_CROSS_GENERATOR" / "results.json").read_text())
