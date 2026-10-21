"""Analytic contracts for the simulator's continuous-time transitions."""

import numpy as np
import pytest
from vigil_sim.mechanisms import (
    draw_poisson_event_times,
    propagate_first_order_secretion,
    shot_noise_at_times,
)


def test_first_order_secretion_matches_analytic_constant_burden_solution():
    rate = 0.03
    secretion = 0.4
    burden = 12.0
    initial = 3.0
    times = np.asarray([0.0, 1.0, 17.5, 100.0])
    actual = propagate_first_order_secretion(
        times, np.full(times.size - 1, burden), initial, secretion, rate
    )
    equilibrium = secretion * burden / rate
    expected = equilibrium + (initial - equilibrium) * np.exp(-rate * times)
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-12)


def test_first_order_secretion_respects_irregular_interval_partition():
    coarse = propagate_first_order_secretion([0.0, 20.0], [7.0], 2.0, 0.5, 0.04)
    fine = propagate_first_order_secretion([0.0, 3.0, 11.0, 20.0], [7.0] * 3, 2.0, 0.5, 0.04)
    assert coarse[-1] == pytest.approx(fine[-1], abs=1e-12)


@pytest.mark.parametrize(
    "args",
    [
        ([], [], 0.0, 1.0, 1.0),
        ([0.0, 1.0], [-1.0], 0.0, 1.0, 1.0),
        ([0.0, 1.0], [1.0], 0.0, 1.0, 0.0),
        ([0.0, 0.0], [1.0], 0.0, 1.0, 1.0),
    ],
)
def test_first_order_secretion_rejects_invalid_inputs(args):
    with pytest.raises(ValueError):
        propagate_first_order_secretion(*args)


def test_poisson_events_are_seeded_and_bounded_by_exposure():
    first = draw_poisson_event_times(60.0, 0.2, np.random.default_rng(19))
    second = draw_poisson_event_times(60.0, 0.2, np.random.default_rng(19))
    np.testing.assert_array_equal(first, second)
    assert np.all((first >= 0.0) & (first <= 60.0))
    assert np.all(np.diff(first) >= 0.0)


def test_shot_noise_superposes_only_prior_events_and_clears_exponentially():
    values = shot_noise_at_times(
        [0.0, 2.0, 5.0], [1.0, 3.0], [4.0, 2.0], clearance_rate_per_day=0.5
    )
    np.testing.assert_allclose(
        values, [0.0, 4.0 * np.exp(-0.5), 4.0 * np.exp(-2.0) + 2.0 * np.exp(-1.0)]
    )


def test_shot_noise_validates_sorted_event_times_and_amplitudes():
    with pytest.raises(ValueError, match="sorted"):
        shot_noise_at_times([2.0], [1.0, 0.0], [1.0, 1.0], 1.0)
    with pytest.raises(ValueError, match="non-negative"):
        shot_noise_at_times([2.0], [1.0], [-1.0], 1.0)
