from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/EXP-CORE-ML-004/run.py"
SPEC = importlib.util.spec_from_file_location("exp_core_ml_004_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
EXP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXP
SPEC.loader.exec_module(EXP)


def test_split_generator_replicate_seeds_are_deterministic_and_disjoint() -> None:
    seeds = {
        EXP.seed_for(split, generator, replicate)
        for split in EXP.SPLIT_OFFSETS
        for generator in EXP.GENERATOR_OFFSETS
        for replicate in EXP.REPLICATES
    }
    assert len(seeds) == len(EXP.SPLIT_OFFSETS) * len(EXP.GENERATOR_OFFSETS) * len(EXP.REPLICATES)
    assert EXP.seed_for("train", "G1", 0) == 44_110
    assert EXP.seed_for("test", "G3", 4) == 44_434


def test_search_grid_matches_the_committed_preregistration() -> None:
    grid = EXP.model_grid()
    assert set(grid) == {"B3_regularized_logistic_horizon", "B4_xgboost_horizon"}
    assert [name for name, _ in grid["B3_regularized_logistic_horizon"]] == [
        "C=0.05",
        "C=0.5",
        "C=5",
    ]
    assert len(grid["B4_xgboost_horizon"]) == 8
    assert len({name for name, _ in grid["B4_xgboost_horizon"]}) == 8


def test_ipcw_metric_bundle_uses_event_and_competing_risk_definitions() -> None:
    frame = pd.DataFrame(
        {
            "patient_id": ["p1", "p2", "p3", "p4"],
            "replicate": [0, 0, 0, 0],
            "follow_up_days": [100.0, 200.0, 400.0, 200.0],
            "event_code": [1, 1, 0, 2],
            "B0_prevalence": [0.5, 0.5, 0.5, 0.5],
            "B1_single_threshold": [0.9, 0.8, 0.2, 0.1],
        }
    )
    result = EXP.metrics_for_replicate(frame, ["B0_prevalence", "B1_single_threshold"])
    assert result["B1_single_threshold.auc"] == 1.0
    assert 0.0 <= result["B1_single_threshold.brier"] <= 1.0
    assert np.isfinite(result["B1_single_threshold.ipcw_ece"])
    assert np.isfinite(result["B1_single_threshold.average_precision"])
    assert result["B0_prevalence.delta_auc_vs_B1"] == -0.5


def test_bootstrap_keeps_patient_clusters_and_requires_registered_valid_draws() -> None:
    rows = []
    for replicate in range(5):
        for patient in range(20):
            event = 1 if patient < 10 else 0
            rows.append(
                {
                    "patient_id": f"r{replicate}:p{patient}",
                    "replicate": replicate,
                    "follow_up_days": 100.0 if event else 400.0,
                    "event_code": event,
                    "B0_prevalence": 0.5,
                    "B1_single_threshold": 0.9 if event else 0.1,
                }
            )
    intervals = EXP.bootstrap_by_patient_and_replicate(
        pd.DataFrame(rows), ["B0_prevalence", "B1_single_threshold"]
    )
    assert intervals["B1_single_threshold.auc"]["ci_95"] == [1.0, 1.0]
    assert intervals["B1_single_threshold.auc"]["valid_replicates"] == EXP.BOOTSTRAPS


def test_undefined_metrics_serialize_as_json_null() -> None:
    serialized = EXP.json_safe({"undefined": float("nan"), "finite": np.float64(0.25)})
    assert serialized == {"undefined": None, "finite": 0.25}
