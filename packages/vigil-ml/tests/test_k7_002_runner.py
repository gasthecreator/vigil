from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO_ROOT / "experiments" / "EXP-S8-K7-002" / "run.py"
SPEC = importlib.util.spec_from_file_location("k7_002_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_k7_runner_fails_closed_without_pre_run_access_record(tmp_path, monkeypatch):
    monkeypatch.setattr(RUNNER, "ACCESS_LOG", tmp_path / "missing-access.jsonl")
    monkeypatch.setattr(RUNNER, "RESULTS", tmp_path / "results.json")
    monkeypatch.setattr(RUNNER, "REPORT", tmp_path / "REPORT.md")
    monkeypatch.setattr(RUNNER, "COMPLETION", tmp_path / "RUN_COMPLETION.json")
    with pytest.raises(RuntimeError, match="access log is missing"):
        RUNNER.validate_access()
    assert not (tmp_path / "results.json").exists()
    assert not (tmp_path / "REPORT.md").exists()
