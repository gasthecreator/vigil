"""Preservation guards for the retired S8-K7 result-producing entrypoint."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "scripts" / "run_study_s8_k7.py"
SPEC = importlib.util.spec_from_file_location("legacy_s8_k7_runner", RUNNER)
assert SPEC is not None and SPEC.loader is not None
RUNNER_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER_MODULE
SPEC.loader.exec_module(RUNNER_MODULE)


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (None, "missing frozen-run disposition"),
        ("not-json", "invalid frozen-run disposition"),
        ('{"status":"active"}', "disposition is not retired"),
    ],
)
def test_legacy_s8_k7_frozen_execution_fails_closed_on_invalid_disposition(
    tmp_path, monkeypatch, contents, message
):
    if contents is not None:
        disposition_path = tmp_path / "experiments" / "EXP-S8-K7-001" / "FROZEN-RUN-DISPOSITION.json"
        disposition_path.parent.mkdir(parents=True)
        disposition_path.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(RUNNER_MODULE, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match=message):
        RUNNER_MODULE.run_study()


def test_legacy_report_writer_refuses_direct_overwrite():
    with pytest.raises(RuntimeError, match="legacy S8-K7 run is retired"):
        RUNNER_MODULE.write_reports({})


def test_legacy_s8_k7_cli_refuses_replay_before_overwriting_historical_outputs():
    outputs = (
        ROOT / "reports" / "ml" / "STUDY_S8_K7_CAUSAL.json",
        ROOT / "reports" / "ml" / "STUDY_S8_K7_CAUSAL.md",
    )
    before = tuple(path.read_bytes() for path in outputs)
    result = subprocess.run(
        [sys.executable, str(RUNNER)], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
    assert "legacy S8-K7 run is retired" in result.stderr
    assert tuple(path.read_bytes() for path in outputs) == before
