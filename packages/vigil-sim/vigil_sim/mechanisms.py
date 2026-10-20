"""Small, independently testable transitions for registered synthetic mechanisms."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Sequence

import numpy as np


def patient_rng(seed: int, patient_id: str, stream: str) -> np.random.Generator:
    """Derive a stable independent random stream for one patient and mechanism."""
    digest = hashlib.sha256(f"{seed}:{patient_id}:{stream}".encode("utf-8")).digest()
    stream_seed = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return np.random.default_rng(stream_seed)


def propagate_first_order_secretion(
    times_days: Sequence[float],
    burden_by_interval: Sequence[float],
    initial_concentration: float,
    secretion_per_burden_day: float,
    clearance_rate_per_day: float,
) -> np.ndarray:
    """Propagate dC/dt = q*B - k*C exactly for piecewise-constant burden."""
    times = np.asarray(times_days, dtype=float)
    burden = np.asarray(burden_by_interval, dtype=float)
    if times.ndim != 1 or times.size < 1 or burden.shape != (times.size - 1,):
        raise ValueError("times must be 1-D and burden must have one value per interval")
    if not np.isfinite(times).all() or not np.isfinite(burden).all():
        raise ValueError("times and burden must be finite")
    if np.any(np.diff(times) <= 0):
        raise ValueError("times must be strictly increasing")
    if not np.isfinite(initial_concentration) or initial_concentration < 0:
        raise ValueError("initial_concentration must be finite and non-negative")
    if not np.isfinite(secretion_per_burden_day) or secretion_per_burden_day < 0:
        raise ValueError("secretion_per_burden_day must be finite and non-negative")
    if not np.isfinite(clearance_rate_per_day) or clearance_rate_per_day <= 0:
        raise ValueError("clearance_rate_per_day must be finite and positive")
    if np.any(burden < 0):
        raise ValueError("burden must be non-negative")

    values = np.empty(times.size, dtype=float)
    values[0] = initial_concentration
    for index, (start, end) in enumerate(zip(times[:-1], times[1:])):
        decay = np.exp(-clearance_rate_per_day * (end - start))
        equilibrium = secretion_per_burden_day * burden[index] / clearance_rate_per_day
        values[index + 1] = values[index] * decay + equilibrium * (1.0 - decay)
    return values


def evaluate_first_order_on_fixed_grid(
    observation_days: Sequence[float],
    burden_at_day: Callable[[float], float],
    secretion_per_burden_day: float,
    clearance_rate_per_day: float,
    integration_step_days: float,
) -> np.ndarray:
    """Integrate on a fixed grid so measurement-visit density cannot change state."""
    observations = np.asarray(observation_days, dtype=float)
    if observations.ndim != 1 or not np.isfinite(observations).all():
        raise ValueError("observation_days must be a finite 1-D sequence")
    if np.any(observations < 0.0) or np.any(np.diff(observations) < 0.0):
        raise ValueError("observation_days must be sorted and non-negative")
    if not np.isfinite(integration_step_days) or integration_step_days <= 0.0:
        raise ValueError("integration_step_days must be finite and positive")
    if not callable(burden_at_day):
        raise ValueError("burden_at_day must be callable")
    if (
        not np.isfinite(secretion_per_burden_day)
        or secretion_per_burden_day < 0.0
        or not np.isfinite(clearance_rate_per_day)
        or clearance_rate_per_day <= 0.0
    ):
        raise ValueError("secretion must be non-negative and clearance must be positive")

    result = np.empty(observations.size, dtype=float)
    if observations.size == 0:
        return result
    state = 0.0
    grid_day = 0.0
    step = integration_step_days
    for index, target in enumerate(observations):
        while grid_day + step <= target:
            burden = float(burden_at_day(grid_day))
            if not np.isfinite(burden) or burden < 0.0:
                raise ValueError("burden_at_day must return finite non-negative values")
            decay = math.exp(-clearance_rate_per_day * step)
            equilibrium = secretion_per_burden_day * burden / clearance_rate_per_day
            state = state * decay + equilibrium * (1.0 - decay)
            grid_day += step
        if target > grid_day:
            burden = float(burden_at_day(grid_day))
            if not np.isfinite(burden) or burden < 0.0:
                raise ValueError("burden_at_day must return finite non-negative values")
            decay = math.exp(-clearance_rate_per_day * (target - grid_day))
            equilibrium = secretion_per_burden_day * burden / clearance_rate_per_day
            result[index] = state * decay + equilibrium * (1.0 - decay)
        else:
            result[index] = state
    return result


def draw_poisson_event_times(
    exposure_days: float, rate_per_day: float, rng: np.random.Generator
) -> np.ndarray:
    """Draw sorted event times from a homogeneous Poisson process on [0, exposure]."""
    if not np.isfinite(exposure_days) or exposure_days < 0:
        raise ValueError("exposure_days must be finite and non-negative")
    if not np.isfinite(rate_per_day) or rate_per_day < 0:
        raise ValueError("rate_per_day must be finite and non-negative")
    count = int(rng.poisson(rate_per_day * exposure_days))
    return np.sort(rng.uniform(0.0, exposure_days, size=count))


def shot_noise_at_times(
    observation_days: Sequence[float],
    event_days: Sequence[float],
    event_amplitudes: Sequence[float],
    clearance_rate_per_day: float,
) -> np.ndarray:
    """Evaluate positive exponential-clearance impulses at arbitrary times."""
    observations = np.asarray(observation_days, dtype=float)
    events = np.asarray(event_days, dtype=float)
    amplitudes = np.asarray(event_amplitudes, dtype=float)
    if observations.ndim != 1 or events.ndim != 1 or amplitudes.shape != events.shape:
        raise ValueError("observation and event times must be 1-D; one amplitude per event")
    if not np.isfinite(observations).all() or not np.isfinite(events).all():
        raise ValueError("observation and event times must be finite")
    if not np.isfinite(amplitudes).all() or np.any(amplitudes < 0):
        raise ValueError("event amplitudes must be finite and non-negative")
    if not np.isfinite(clearance_rate_per_day) or clearance_rate_per_day <= 0:
        raise ValueError("clearance_rate_per_day must be finite and positive")
    if np.any(np.diff(events) < 0):
        raise ValueError("event times must be sorted")
    elapsed = observations[:, None] - events[None, :]
    contributions = amplitudes[None, :] * np.exp(-clearance_rate_per_day * np.maximum(elapsed, 0.0))
    contributions[elapsed < 0.0] = 0.0
    return np.asarray(contributions.sum(axis=1), dtype=float)
