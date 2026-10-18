"""vigil_sim.multilab: a laboratory layer on top of a simulated clinical cohort.

Written for EXP-K5-001 (`experiments/EXP-K5-001/PREREG.md`, section 3). It takes the observed CA 15-3 values of
a `CohortDataset`, assigns every patient a home laboratory, lets a fraction of patients switch laboratory part-way
through follow-up, and multiplies every result by the proportional bias `exp(beta_lab)` of the laboratory that
produced it (optionally with a step change at a calendar day). The true offsets are returned *separately* from the
observation table so that an estimator can be given only what a real deployment would have: patient, visit time,
laboratory and value.

Synthetic only. Nothing here is evidence about real laboratories; the spread `tau` is a parameter, anchored for
the sourced scenario by E23 and an assumption elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

HOME_PROBS_NET = (0.25, 0.20, 0.20, 0.15, 0.10, 0.10)
ENTRY_WINDOW_DAYS = 540.0


@dataclass(frozen=True)
class LabShift:
    """A step change of `delta` (log units) in laboratory `lab` for results drawn on or after `calendar_day`."""

    lab: int
    delta: float
    calendar_day: float


@dataclass(frozen=True)
class MultiLabConfig:
    tau: float
    switch_fraction: float
    seed: int
    n_net_labs: int = 6
    case_mix: bool = False
    #: "network": home laboratories 0..n_net-1, switch among network laboratories; "new_site_training":
    #: network assignment plus `new_site_switchers` switching patients per new laboratory; "new_site_eval":
    #: home in the network, switchers (fraction switch_fraction) go to a new laboratory (ids n_net..).
    mode: str = "network"
    new_site_switchers: int = 0
    n_new_labs: int = 2
    shift: Optional[LabShift] = None
    home_probs: Tuple[float, ...] = HOME_PROBS_NET


@dataclass
class MultiLabCohort:
    """`observations` carries only what an estimator may see (plus `y_clean` for truth-based checks)."""

    observations: pd.DataFrame  # patient_id, visit_idx, day, calendar_day, lab, y
    patients: pd.DataFrame  # clinical truth: stage, true_recurrence_event, true_recurrence_day, home_lab
    true_beta: Dict[int, float]
    config: MultiLabConfig
    y_clean: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))

    @property
    def n_labs(self) -> int:
        return len(self.true_beta)


def _home_lab(rng: np.random.Generator, stage: str, cfg: MultiLabConfig) -> int:
    n = cfg.n_net_labs
    if cfg.case_mix and n >= 6:
        advanced = stage in ("III", "IV", "STAGE_III", "STAGE_IV", "Stage III", "Stage IV")
        high_labs, other_labs = [0, 1], list(range(2, n))
        p_high = 0.80 if advanced else 0.20
        if rng.random() < p_high:
            return int(rng.choice(high_labs))
        return int(rng.choice(other_labs))
    p = np.asarray(cfg.home_probs, dtype=float)
    p = p / p.sum()
    return int(rng.choice(n, p=p))


def draw_true_beta(seed: int, tau: float, n_labs: int) -> Dict[int, float]:
    """True log-scale offsets, one per laboratory. Drawn once per replication and shared by the training and
    evaluation layers so that both see the same laboratories."""
    rng = np.random.default_rng(seed)
    return {lab: float(rng.normal(0.0, tau)) for lab in range(n_labs)}


def apply_multilab(
    observations: pd.DataFrame,
    patients: pd.DataFrame,
    cfg: MultiLabConfig,
    true_beta: Dict[int, float],
    marker: str = "ca_15_3",
) -> MultiLabCohort:
    """Build the laboratory layer.

    `observations` is `CohortDataset.to_observations_dataframe()` (only `patient_id`, `day`, `marker` are used)
    and `patients` is `CohortDataset.to_patients_dataframe()`.
    """
    rng = np.random.default_rng(cfg.seed)
    n_total_labs = cfg.n_net_labs + (cfg.n_new_labs if cfg.mode != "network" else 0)
    missing = [lab for lab in range(n_total_labs) if lab not in true_beta]
    if missing:
        raise ValueError(f"true_beta lacks laboratories {missing}")
    beta = {lab: float(true_beta[lab]) for lab in range(n_total_labs)}

    obs = observations[["patient_id", "day", marker]].dropna(subset=[marker])
    obs = obs[obs[marker] > 0].copy()
    obs = obs.sort_values(["patient_id", "day"]).reset_index(drop=True)
    obs["visit_idx"] = obs.groupby("patient_id").cumcount()
    n_by_patient = obs.groupby("patient_id").size()

    pat = patients.set_index("patient_id")
    ids = list(n_by_patient.index)
    entry = {pid: float(rng.uniform(0.0, ENTRY_WINDOW_DAYS)) for pid in ids}
    home: Dict[str, int] = {pid: _home_lab(rng, str(pat.loc[pid, "stage"]), cfg) for pid in ids}

    # switchers: (patient -> (switch_visit_idx, other_lab))
    switch: Dict[str, Tuple[int, int]] = {}
    eligible = [pid for pid in ids if n_by_patient[pid] >= 3]
    for pid in eligible:
        if rng.random() < cfg.switch_fraction:
            if cfg.mode == "new_site_eval":
                targets = list(range(cfg.n_net_labs, cfg.n_net_labs + cfg.n_new_labs))
            else:
                targets = [lab for lab in range(cfg.n_net_labs) if lab != home[pid]]
            switch[pid] = (int(rng.integers(1, int(n_by_patient[pid]) - 1)), int(rng.choice(targets)))
    if cfg.mode == "new_site_training" and cfg.new_site_switchers > 0:
        pool = [pid for pid in eligible if pid not in switch]
        rng.shuffle(pool)
        take = 0
        for new_lab in range(cfg.n_net_labs, cfg.n_net_labs + cfg.n_new_labs):
            for _ in range(cfg.new_site_switchers):
                if take >= len(pool):
                    break
                pid = pool[take]
                take += 1
                switch[pid] = (int(rng.integers(1, int(n_by_patient[pid]) - 1)), new_lab)

    labs = np.empty(len(obs), dtype=np.int64)
    for k, (pid, vidx) in enumerate(zip(obs["patient_id"].to_numpy(), obs["visit_idx"].to_numpy())):
        if pid in switch and vidx >= switch[pid][0]:
            labs[k] = switch[pid][1]
        else:
            labs[k] = home[pid]
    obs["lab"] = labs
    obs["calendar_day"] = obs["day"].to_numpy(dtype=float) + obs["patient_id"].map(entry).to_numpy(
        dtype=float
    )

    y_clean = obs[marker].to_numpy(dtype=float)
    log_bias = np.array([beta[int(lab)] for lab in labs], dtype=float)
    if cfg.shift is not None:
        in_shift = (labs == cfg.shift.lab) & (obs["calendar_day"].to_numpy() >= cfg.shift.calendar_day)
        log_bias = log_bias + np.where(in_shift, cfg.shift.delta, 0.0)
    obs["y"] = y_clean * np.exp(log_bias)

    keep = obs[["patient_id", "visit_idx", "day", "calendar_day", "lab", "y"]].copy()
    pt = patients[
        ["patient_id", "stage", "true_recurrence_event", "true_recurrence_day"]
    ].copy()
    pt["home_lab"] = pt["patient_id"].map(home)
    pt = pt[pt["patient_id"].isin(ids)].reset_index(drop=True)
    return MultiLabCohort(
        observations=keep, patients=pt, true_beta=beta, config=cfg, y_clean=y_clean
    )


def pairwise_contrast_truth(beta: Dict[int, float], labs: Sequence[int]) -> List[Tuple[int, int, float]]:
    """True contrasts beta_a - beta_b for every unordered pair (gauge-free)."""
    out: List[Tuple[int, int, float]] = []
    labs = list(labs)
    for i, a in enumerate(labs):
        for b in labs[i + 1 :]:
            out.append((a, b, beta[a] - beta[b]))
    return out
