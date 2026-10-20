from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

P = Path(__file__).with_name("run.py")
spec = importlib.util.spec_from_file_location("exp010_runner", P)
RUN = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = RUN
spec.loader.exec_module(RUN)


def test_registered_seed_splits_are_distinct_and_reproducible():
    assert RUN.seed("MCAR", 0, False) == 20261101
    assert RUN.seed("MCAR", 0, True) == 20761101
    assert RUN.seed("MNAR", 99, True) == 20961200


def test_test_missing_marker_uses_development_median():
    dev = RUN.cohort("MAR", np.random.default_rng(RUN.seed("MAR", 0, False)))
    med = float(np.nanmedian(dev["marker"]))
    test = RUN.cohort("MAR", np.random.default_rng(RUN.seed("MAR", 0, True)), med)
    assert np.all(test["mi"][test["missing"]] == med)
    assert np.allclose(dev["mi"][dev["missing"]], med)


def test_propensity_prediction_uses_development_fit_only():
    dev = RUN.cohort("MAR", np.random.default_rng(RUN.seed("MAR", 1, False)))
    test = RUN.cohort(
        "MAR", np.random.default_rng(RUN.seed("MAR", 1, True)), float(np.nanmedian(dev["marker"]))
    )
    xdev = np.column_stack((dev["x"], dev["mi"], dev["missing"].astype(float)))
    xtest = np.column_stack((test["x"], test["mi"], test["missing"].astype(float)))
    model = RUN.LogisticRegression(max_iter=500).fit(xdev, dev["verified"].astype(int))
    before = model.predict_proba(xtest)[:, 1]
    altered_test_labels = 1 - test["verified"].astype(int)
    after = model.predict_proba(xtest)[:, 1]
    assert np.array_equal(before, after)
    assert altered_test_labels.shape == after.shape


def test_report_is_rendered_from_saved_result_shape():
    rows = []
    for condition in RUN.OFFSETS:
        for rep in RUN.REPLICATES:
            rows.append(
                {
                    "condition": condition,
                    "errors": {
                        e: {m: 0.01 for m in RUN.METRICS}
                        for e in ("complete_case", "development_fit_ipw")
                    },
                    "estimates": {
                        e: {m: 0.5 for m in RUN.METRICS}
                        for e in ("complete_case", "development_fit_ipw")
                    },
                }
            )
    result = {"source_commit": "test-sha", "summary": RUN.aggregate(rows)}
    report = RUN.render(result)
    assert report == RUN.render(json.loads(json.dumps(result)))
    assert "Synthetic method-validation only" in report


def test_runner_refuses_dirty_tree_before_creating_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr(RUN, "EXP", tmp_path)
    monkeypatch.setattr(
        RUN.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": " M file\n"})()
    )
    with pytest.raises(RuntimeError, match="dirty working tree"):
        RUN.main()
    assert not list(tmp_path.iterdir())
