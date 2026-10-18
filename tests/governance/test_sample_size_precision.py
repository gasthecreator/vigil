"""scripts/sample_size_precision.py: precision-based sample sizes (events and patients)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import sample_size_precision as ssp  # noqa: E402


def test_normal_approximation_matches_the_closed_form():
    assert ssp.n_normal(0.5, 0.05) == math.ceil(1.959963984540054**2 * 0.25 / 0.05**2) == 385


@pytest.mark.parametrize("p,d", [(0.5, 0.05), (0.8, 0.1), (0.9, 0.05), (0.7, 0.15)])
def test_wilson_n_is_the_smallest_n_with_halfwidth_at_most_d(p, d):
    n = ssp.n_wilson(p, d)
    assert ssp.wilson_halfwidth(p, n) <= d + 1e-12
    assert ssp.wilson_halfwidth(p, n - 1) > d


def test_more_precision_needs_more_events_and_rarer_outcomes_need_more_patients():
    assert ssp.n_wilson(0.8, 0.05) > ssp.n_wilson(0.8, 0.10)
    assert ssp.patients_for_events(100, 0.05) > ssp.patients_for_events(100, 0.20)
    assert ssp.patients_for_events(100, 0.10) == 1000


def test_invalid_inputs_are_rejected():
    for bad in ((0.0, 0.1), (1.0, 0.1), (0.5, 0.0), (0.5, 0.6)):
        with pytest.raises(ValueError):
            ssp.n_wilson(*bad)
    with pytest.raises(ValueError):
        ssp.patients_for_events(10, 0.0)
