import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest
from vigil_ml.m3 import DEFAULT_M3_ASSUMPTIONS, adjudicate, load_m3_assumptions

RUNNER_PATH = Path(__file__).resolve().parents[3] / "experiments" / "EXP-M3-001" / "run.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("exp_m3_001_runner", RUNNER_PATH)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER)


def test_default_m3_configuration_is_versioned_synthetic_research_only():
    config = load_m3_assumptions()
    assert config == DEFAULT_M3_ASSUMPTIONS
    assert config.config_id == "m3_synthetic_contract_v1"
    assert config.status == "synthetic_research_assumptions"
    assert config.gross_error_mode_weights == pytest.approx((1 / 3, 1 / 3, 1 / 3))


def test_sensitivity_runner_pins_audited_simulator_profile():
    profile_path = RUNNER.SIMULATOR_PROFILE_PATH
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile_path.name == "synthetic_population_core_v4.json"
    assert profile["profile_id"] == "balanced_synthetic_core_v4"


@pytest.mark.parametrize(
    "changes",
    [
        {"p_error_prior": 1.0},
        {"real_change_ratio_min": 3.0},
        {"gross_error_mode_weights": (0.2, 0.2, 0.2)},
        {"decimal_shift_factor": 1.0},
        {"stable_explained_threshold": 1.1},
        {"status": "clinically_validated"},
        {"config_sha256": "not-a-hash"},
    ],
)
def test_invalid_assumptions_are_rejected(changes):
    with pytest.raises(ValueError):
        replace(DEFAULT_M3_ASSUMPTIONS, **changes)


def test_unknown_config_schema_is_rejected(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported M3 assumptions schema version"):
        load_m3_assumptions(config_path)


def test_configuration_hash_tracks_exact_file_bytes(tmp_path: Path):
    source = RUNNER.CONFIG_PATH.read_bytes()
    copy = tmp_path / "m3.json"
    copy.write_bytes(source + b"\n")
    assert load_m3_assumptions(copy).config_sha256 != DEFAULT_M3_ASSUMPTIONS.config_sha256


def test_configuration_rejects_misordered_error_modes(tmp_path: Path):
    payload = json.loads(RUNNER.CONFIG_PATH.read_text(encoding="utf-8"))
    payload["gross_error"]["modes"].reverse()
    path = tmp_path / "misordered.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="supported ordering"):
        load_m3_assumptions(path)


def test_versioned_config_values_match_historical_contract_defaults():
    config = DEFAULT_M3_ASSUMPTIONS
    assert (config.p_error_prior, config.p_real_prior, config.inter_lab_cv) == (0.03, 0.20, 0.10)
    assert (config.real_change_ratio_min, config.real_change_ratio_max) == (1.4, 3.0)
    assert (config.error_needs_repeat_threshold, config.real_change_escalate_threshold) == (0.30, 0.60)
    assert config.stable_explained_threshold == 0.90


def test_adjudication_records_the_assumption_configuration_used():
    history = [(0.0, 20.0), (30.0, 21.0)]
    inputs = dict(
        history=history,
        new_day=60.0,
        new_value=23.0,
        cv_analytical=0.05,
        cv_within=0.10,
    )
    config = replace(
        DEFAULT_M3_ASSUMPTIONS,
        config_id="registered_sensitivity_variant",
        p_error_prior=0.10,
    )
    result = adjudicate(**inputs, assumptions=config)
    baseline = adjudicate(**inputs)
    assert result["assumption_config_id"] == "registered_sensitivity_variant"
    assert result["assumption_status"] == "synthetic_research_assumptions"
    assert result["assumption_config_sha256"] == config.effective_config_sha256
    assert result["assumption_config_sha256"] != baseline["assumption_config_sha256"]
    assert result["assumption_source_sha256"] == DEFAULT_M3_ASSUMPTIONS.config_sha256
    assert result["p_error"] != baseline["p_error"]


def test_registered_sensitivity_grid_is_complete_and_one_factor_at_a_time():
    configurations = RUNNER.registered_configurations()
    assert len(configurations) == 23
    assert len({config.config_id for config in configurations}) == 23
    baseline = configurations[0]
    grouped_fields = (
        {"p_error_prior"},
        {"p_real_prior"},
        {"real_change_ratio_min", "real_change_ratio_max"},
        {"population_error_log_median"},
        {"population_error_log_sd"},
        {"inter_lab_cv"},
        {"decimal_shift_factor"},
        {"gross_error_mode_weights"},
        {"error_needs_repeat_threshold"},
        {"real_change_escalate_threshold"},
        {"stable_explained_threshold"},
    )
    for config in configurations[1:]:
        changed = {
            key
            for key, value in vars(config).items()
            if key != "config_id" and value != vars(baseline)[key]
        }
        assert any(changed and changed <= allowed for allowed in grouped_fields)
