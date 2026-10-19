"""Non-data-access checks for the EXP-CORE-ML-007 runner contract."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

RUNNER_PATH = Path(__file__).with_name("run.py")
SPEC = importlib.util.spec_from_file_location("exp_core_ml_007_run", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_registered_seed_tuples_are_unique_and_outside_exp_004_range():
    seeds = [
        RUNNER.seed_for(split, generator, replicate)
        for split, generators in (
            ("train", ("G1", "G2")),
            ("calibration", ("G1", "G2")),
            ("validation", ("G1", "G2")),
            ("test", ("G1", "G2", "G3")),
        )
        for generator in generators
        for replicate in RUNNER.REPLICATES
    ]
    assert len(seeds) == len(set(seeds))
    assert min(seeds) > 44_500


def test_profile_hash_matches_preregistration():
    assert RUNNER.hashlib.sha256(RUNNER.PROFILE_PATH.read_bytes()).hexdigest() == (
        "70cfed8bfe8c28c668434b5e409d2350b276784461f54a56e3ecd69ae98469b3"
    )


def test_runner_refuses_existing_output_or_prior_test_access(tmp_path, monkeypatch):
    monkeypatch.setattr(RUNNER, "ROOT", tmp_path)
    output = tmp_path / "experiments/EXP-CORE-ML-007/results.json"
    output.parent.mkdir(parents=True)
    output.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="output already exists"):
        RUNNER.assert_no_prior_run()

    output.unlink()
    access_log = tmp_path / "data/audit/frozen_test_access.jsonl"
    access_log.parent.mkdir(parents=True)
    access_log.write_text(
        json.dumps({"dataset_name": "SYNTHETIC-CORE-ML-007-G1-TEST"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="access is already logged"):
        RUNNER.assert_no_prior_run()
