"""K5 invariants (experiments/EXP-K5-001/PREREG.md section 8), tested before the frozen run."""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path

import numpy as np
import pytest
from vigil_ml import k5

ROOT = Path(__file__).resolve().parents[3]


def synth(seed=0, n_pat=120, n_labs=4, tau=0.15, sigma=0.05, p_switch=0.4, trend=True):
    """Patients with log-linear trajectories, results at one or two laboratories."""
    rng = np.random.default_rng(seed)
    beta = rng.normal(0, tau, n_labs)
    P, T, LAB, Y = [], [], [], []
    for i in range(n_pat):
        a, b = rng.normal(3.0, 0.5), (rng.normal(0, 0.001) if trend else 0.0)
        n = int(rng.integers(3, 8))
        t = np.sort(rng.uniform(0, 700, n))
        home = int(rng.integers(0, n_labs))
        other = int(rng.choice([x for x in range(n_labs) if x != home]))
        k_sw = int(rng.integers(1, n - 1)) if rng.random() < p_switch else n
        for j in range(n):
            lab = home if j < k_sw else other
            P.append(i), T.append(t[j]), LAB.append(f"L{lab}")
            Y.append(math.exp(a + b * t[j] + beta[lab] + rng.normal(0, sigma)))
    return np.array(P), np.array(T), np.array(LAB), np.array(Y), beta


def contrast_err(fit, beta):
    errs = []
    for a in range(len(beta)):
        for b in range(a + 1, len(beta)):
            est, _ = fit.contrast(f"L{a}", f"L{b}")
            errs.append(est - (beta[a] - beta[b]))
    return np.array(errs)


def test_noise_free_connected_design_recovers_contrasts_to_numerical_precision():
    P, T, LAB, Y, beta = synth(sigma=0.0, trend=True)
    sysm = k5.build_projected_system(P, T, LAB, Y)
    assert np.abs(contrast_err(k5.fit_fixed(sysm), beta)).max() < 1e-8
    # K5 with a vanishing amount of shrinkage (rho large) is the same solution
    assert np.abs(contrast_err(k5.posterior_at_rho(sysm, 1e9), beta)).max() < 1e-6


def test_k5_recovers_contrasts_with_noise_and_beats_pooled_error():
    P, T, LAB, Y, beta = synth(seed=3, sigma=0.05)
    fit = k5.fit_k5(k5.build_projected_system(P, T, LAB, Y))
    err = contrast_err(fit, beta)
    pooled = np.array([beta[a] - beta[b] for a in range(4) for b in range(a + 1, 4)])
    assert np.sqrt(np.mean(err**2)) < 0.35 * np.sqrt(np.mean(pooled**2))
    assert 0.03 < fit.tau < 0.5  # REML tau is in the right region (true 0.15)


def test_rho_limits_zero_and_fixed():
    P, T, LAB, Y, _ = synth(seed=4)
    sysm = k5.build_projected_system(P, T, LAB, Y)
    assert np.abs(k5.posterior_at_rho(sysm, 1e-10).beta).max() < 1e-6
    big = k5.posterior_at_rho(sysm, 1e10)
    fixed = k5.fit_fixed(sysm)
    # identical up to the (unidentified) gauge: contrasts agree
    for a, b in [("L0", "L1"), ("L1", "L3"), ("L0", "L2")]:
        assert big.contrast(a, b)[0] == pytest.approx(fixed.contrast(a, b)[0], abs=1e-5)


def test_relabelling_permutes_estimates_and_constant_shift_changes_no_contrast():
    P, T, LAB, Y, beta = synth(seed=5)
    base = k5.fit_k5(k5.build_projected_system(P, T, LAB, Y))
    perm = {"L0": "L2", "L1": "L0", "L2": "L3", "L3": "L1"}
    relabelled = k5.fit_k5(k5.build_projected_system(P, T, np.array([perm[x] for x in LAB]), Y))
    for old, new in perm.items():
        assert relabelled.beta[relabelled.lab_ids.index(new)] == pytest.approx(
            base.beta[base.lab_ids.index(old)], abs=1e-9
        )
    # multiplying every result by a constant (adding a constant to every offset) changes no contrast
    scaled = k5.fit_k5(k5.build_projected_system(P, T, LAB, Y * 1.7))
    for a, b in [("L0", "L1"), ("L2", "L3")]:
        assert scaled.contrast(a, b)[0] == pytest.approx(base.contrast(a, b)[0], abs=1e-9)


def test_unconnected_or_unseen_laboratory_keeps_its_prior():
    P, T, LAB, Y, _ = synth(seed=6, n_labs=3)
    # laboratory X: patients tested only there (no switching), so nothing connects it
    rng = np.random.default_rng(1)
    extra = []
    for i in range(1000, 1040):
        t = np.sort(rng.uniform(0, 700, 5))
        for tj in t:
            extra.append((i, tj, "LX", math.exp(3.0 + rng.normal(0, 0.05))))
    P2 = np.r_[P, [e[0] for e in extra]]
    T2 = np.r_[T, [e[1] for e in extra]]
    L2 = np.r_[LAB, [e[2] for e in extra]]
    Y2 = np.r_[Y, [e[3] for e in extra]]
    fit = k5.fit_k5(k5.build_projected_system(P2, T2, L2, Y2))
    assert abs(fit.beta[fit.lab_ids.index("LX")]) < 1e-9
    est, sd = fit.contrast("LX", "NEVER_SEEN")
    assert est == pytest.approx(0.0, abs=1e-9)
    assert sd == pytest.approx(math.sqrt(2) * fit.tau, rel=1e-6)
    est2, sd2 = k5.fit_fixed(k5.build_projected_system(P2, T2, L2, Y2)).contrast("LX", "NEVER_SEEN")
    assert math.isinf(sd2)


def test_patients_with_fewer_than_three_results_carry_no_information():
    P, T, LAB, Y, _ = synth(seed=7)
    base = k5.build_projected_system(P, T, LAB, Y)
    rng = np.random.default_rng(2)
    P2 = np.r_[P, np.arange(5000, 5100).repeat(2)]
    T2 = np.r_[T, np.tile([0.0, 100.0], 100)]
    L2 = np.r_[LAB, rng.choice(["L0", "L1"], 200)]
    Y2 = np.r_[Y, rng.uniform(5, 50, 200)]
    more = k5.build_projected_system(P2, T2, L2, Y2)
    assert np.allclose(more.A, base.A) and np.allclose(more.b, base.b)
    assert more.df == base.df


def test_invalid_values_are_refused():
    with pytest.raises(ValueError):
        k5.build_projected_system([1, 1, 1], [0, 1, 2], ["a", "a", "b"], [1.0, -2.0, 3.0])


def test_safetensors_and_onnx_parity(tmp_path):
    ort = pytest.importorskip("onnxruntime")
    P, T, LAB, Y, _ = synth(seed=8)
    h = k5.LabHarmoniserK5("ca_15_3").fit(P, T, LAB, Y)
    st = tmp_path / "k5.safetensors"
    h.save_safetensors(st)
    h2 = k5.LabHarmoniserK5.load_safetensors(st)
    assert h2.offsets() == h.offsets()
    labs = list(LAB[:50]) + ["UNSEEN"] * 3
    vals = np.r_[Y[:50], [10.0, 20.0, 30.0]]
    expected = h.harmonise(labs, vals)
    assert np.array_equal(h2.harmonise(labs, vals), expected)
    onnx_path = tmp_path / "k5.onnx"
    order = h.export_onnx(onnx_path)
    idx = np.array([order.index(x) if x in order else len(order) for x in labs], dtype=np.int64)
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    out = sess.run(["harmonised"], {"value": vals.astype(np.float64), "lab_index": idx})[0]
    assert np.max(np.abs(out - expected)) < 1e-6


def test_unseen_laboratory_is_left_unchanged():
    P, T, LAB, Y, _ = synth(seed=9)
    h = k5.LabHarmoniserK5().fit(P, T, LAB, Y)
    assert h.harmonise(["NEW"], [12.5])[0] == 12.5


def test_estimator_module_cannot_see_simulator_or_truth():
    src = (ROOT / "packages" / "vigil-ml" / "vigil_ml" / "k5.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "vigil_sim" not in imported
    assert "latent_" not in src and "true_beta" not in src
    params = inspect.signature(k5.build_projected_system).parameters
    assert list(params) == ["patient", "t_days", "lab", "value"]


def test_residuals_use_only_earlier_results_of_the_same_patient():
    P = np.array([1, 1, 1, 2, 2])
    cal = np.array([10.0, 30.0, 20.0, 5.0, 6.0])
    h = np.array([1.0, 3.0, 2.0, 10.0, 11.0])
    r = k5.one_step_residuals(P, cal, h)
    assert np.isnan(r[0]) and np.isnan(r[3])
    assert r[2] == pytest.approx(2.0 - 1.0)  # cal 20: previous is cal 10 only
    assert r[1] == pytest.approx(3.0 - 1.5)  # cal 30: previous cal 10, 20
    assert r[4] == pytest.approx(1.0)


def test_cusum_detects_a_step_and_calibration_controls_the_null():
    rng = np.random.default_rng(10)
    null = [rng.normal(0, 1, 1500) for _ in range(20)]
    h = k5.calibrate_cusum_threshold(null, slack=0.5, max_alarms_per_obs=1 / 1500)
    assert 2.0 <= h <= 15.0
    # fresh null streams: alarm rate near or below the target (loose: sampling noise)
    fresh = [rng.normal(0, 1, 1500) for _ in range(20)]
    alarms = 0
    for stream in fresh:
        c = 0.0
        for x in stream:
            c = max(0.0, c + x - 0.5)
            if c >= h:
                alarms += 1
                c = 0.0
    # target: at most one alarm per 1,500 results = 20 over 30,000; allow twice that for sampling noise
    assert alarms <= 40
    shifted = np.r_[rng.normal(0, 1, 200), rng.normal(1.5, 1, 200)]
    idx = k5.cusum_first_alarm(shifted, 0.5, h)
    assert idx is not None and 200 <= idx < 260
    assert k5.cusum_first_alarm(np.zeros(100), 0.5, 2.0) is None


def test_old_s5_is_retracted_and_cannot_produce_numbers():
    import pytest as _pt
    from vigil_ml.harmonisation_k5 import HierarchicalLabHarmoniserK5

    with _pt.raises(NotImplementedError):
        HierarchicalLabHarmoniserK5().run_study_s5()
    assert not (ROOT / "reports" / "ml" / "S5_HARMONISATION").exists()
    assert (ROOT / "reports" / "ml" / "RETRACTED" / "S5_HARMONISATION_V1" / "REPORT.md").exists()
    src = (ROOT / "scripts" / "run_benchmarks.py").read_text(encoding="utf-8")
    assert "34.2" not in src and "S5_HARMONISATION/REPORT" not in src


def test_model_registry_is_current_and_cites_real_tests():
    import subprocess
    import sys

    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_model_registry.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stdout + out.stderr
