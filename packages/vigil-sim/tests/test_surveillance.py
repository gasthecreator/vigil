"""Dense surveillance worlds (EXP-K6-001, PREREG section 3)."""

from __future__ import annotations

import numpy as np
import pytest
from vigil_sim import GeneratorType
from vigil_sim.surveillance import (
    ANALYTES,
    BURDEN_DETECTABLE,
    ELIGIBLE_MIN_RECURRENCE_DAY,
    GRID_START,
    N_GRID,
    build_world,
    grid_days,
)


@pytest.fixture(scope="module")
def world():
    return build_world(GeneratorType.G1_SMOOTH, seed=4242, n_generated=60)


def test_grid_is_weekly_from_day_182_to_day_1820():
    d = grid_days()
    assert d[0] == GRID_START == 182.0 and d[-1] == 1820.0 and len(d) == N_GRID == 235
    assert np.all(np.diff(d) == 7.0)


def test_shapes_and_eligibility(world):
    n = world.n
    assert world.values.shape == (n, N_GRID, len(ANALYTES))
    assert world.measured.shape == world.values.shape and world.burden.shape == (n, N_GRID)
    assert world.meta["n_eligible"] == n <= world.meta["n_generated"] == 60
    rec = world.has_rec
    assert (world.t_rec[rec] >= ELIGIBLE_MIN_RECURRENCE_DAY).all()
    assert (world.comp_day >= GRID_START).all()


def test_detectable_and_presentation_indices_are_first_crossings(world):
    for i in range(world.n):
        idx = np.flatnonzero(world.burden[i] >= BURDEN_DETECTABLE)
        assert world.t_det_idx[i] == (idx[0] if idx.size else N_GRID)
        idx3 = np.flatnonzero(world.max_sym[i] >= 3)
        assert world.sym3_idx[i] == (idx3[0] if idx3.size else N_GRID)


def test_a_world_is_deterministic_for_a_seed_and_differs_across_seeds(world):
    again = build_world(GeneratorType.G1_SMOOTH, seed=4242, n_generated=60)
    assert np.array_equal(world.values, again.values) and np.array_equal(world.burden, again.burden)
    other = build_world(GeneratorType.G1_SMOOTH, seed=4243, n_generated=60)
    assert other.values.shape != world.values.shape or not np.array_equal(other.values, world.values)


@pytest.mark.parametrize("gen", [GeneratorType.G2_BURST, GeneratorType.G3_NOISE])
def test_other_generators_build_a_world(gen):
    w = build_world(gen, seed=7, n_generated=25)
    assert w.n > 0 and np.isfinite(w.values[w.measured]).all()
