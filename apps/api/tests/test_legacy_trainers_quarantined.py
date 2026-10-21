"""Legacy training entry points must not create unreviewed model artifacts."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from vigil_api.ml.train_baseline import train_baseline_model
from vigil_api.ml.train_lstm import train_lstm_model


@pytest.mark.parametrize(
    "trainer",
    [
        train_baseline_model,
        train_lstm_model,
    ],
)
def test_legacy_trainer_functions_fail_closed_without_writing(
    trainer: Callable[..., None], tmp_path: Path
) -> None:
    with pytest.raises(RuntimeError, match="quarantined"):
        trainer(str(tmp_path))

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "module", ["vigil_api.ml.train_baseline", "vigil_api.ml.train_lstm"]
)
def test_legacy_training_modules_are_not_executable(module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", module],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert result.returncode != 0
    assert "quarantined" in result.stderr
