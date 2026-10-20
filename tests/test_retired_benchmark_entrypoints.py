from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_benchmarks.py"
SPEC = importlib.util.spec_from_file_location("retired_run_benchmarks", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

LEAKAGE_SCRIPT = ROOT / "scripts" / "compare_leaky_vs_clean.py"
LEAKAGE_SPEC = importlib.util.spec_from_file_location("retired_leakage_comparison", LEAKAGE_SCRIPT)
assert LEAKAGE_SPEC is not None and LEAKAGE_SPEC.loader is not None
LEAKAGE_MODULE = importlib.util.module_from_spec(LEAKAGE_SPEC)
LEAKAGE_SPEC.loader.exec_module(LEAKAGE_MODULE)


@pytest.mark.parametrize("entrypoint", [MODULE.run_study_s1, MODULE.run_study_s9])
def test_retired_studies_fail_before_data_access_or_fitting(entrypoint) -> None:
    with pytest.raises(RuntimeError, match="retired"):
        entrypoint(audit_logger=None)


def test_retired_aggregate_runner_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="retired"):
        MODULE.main()


def test_historical_leakage_comparison_fails_before_data_access_or_writing(monkeypatch) -> None:
    artifact = ROOT / "reports" / "ml" / "LEAKAGE_DELTA.json"
    original = artifact.read_bytes()
    monkeypatch.setattr(
        LEAKAGE_MODULE,
        "get_generator",
        lambda *_args, **_kwargs: pytest.fail("retired runner accessed simulator data"),
    )
    with pytest.raises(RuntimeError, match="retired"):
        LEAKAGE_MODULE.run_comparison()
    assert artifact.read_bytes() == original


@pytest.mark.parametrize(
    "renderer,args",
    [
        (MODULE.render_s1_markdown, ({},)),
        (MODULE.render_s3_markdown, ({},)),
        (MODULE.render_s9_markdown, ({},)),
    ],
)
def test_retired_study_renderers_do_not_write_reports(renderer, args, tmp_path) -> None:
    target = tmp_path / "historical-report.md"
    with pytest.raises(RuntimeError, match="retired"):
        renderer(*args, path=target)
    assert not target.exists()


def test_retired_master_renderer_does_not_overwrite_benchmark_report(tmp_path) -> None:
    target = tmp_path / "benchmark-report.md"
    with pytest.raises(RuntimeError, match="retired"):
        MODULE.render_master_benchmark_report({}, {}, {}, {}, path=target)
    assert not target.exists()
