"""Dense surveillance worlds for schedule studies (EXP-K6-001, PREREG section 3).

The cohort generators produce one trajectory per patient for the visit days they are given. A schedule
study needs the *same patient* observed at whatever days a policy chooses, so a world here is built by
calling a generator once per patient on a weekly grid; a policy then picks grid days. Every generator is
a function of the day only (its random draws per patient are made once per call), so one dense call is
equivalent to calling it at the chosen days, and two policies that visit the same day see the same
measurement.

``DenseWorld`` keeps two kinds of arrays:
  * observation arrays (``values``, ``measured``, ``max_sym``, ``static``) that a policy may see, and
  * environment and truth arrays (``burden``, ``has_rec``, ``t_rec``, ``comp_day``, ``t_det_idx``,
    ``sym3_idx``) used only by the simulation of imaging and by labels and endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np

from vigil_sim.generators import (
    BreastCancerSubtype,
    GeneratorType,
    PresentationStage,
    get_generator,
)

GRID_START: float = 182.0
GRID_STEP: float = 7.0
N_GRID: int = 235  # days 182 .. 1820
ELIGIBLE_MIN_RECURRENCE_DAY: float = 210.0
BURDEN_DETECTABLE: float = 12.0
SYMPTOM_PRESENTATION_GRADE: int = 3
ANALYTES: Tuple[str, ...] = ("alp", "ggt", "ast", "alt", "ca_15_3", "cea")
_STAGE = {
    PresentationStage.STAGE_I: 1,
    PresentationStage.STAGE_II: 2,
    PresentationStage.STAGE_III: 3,
    PresentationStage.STAGE_IV: 4,
}


def grid_days() -> np.ndarray:
    return GRID_START + GRID_STEP * np.arange(N_GRID)


@dataclass
class DenseWorld:
    generator: str
    seed: int
    day: np.ndarray  # (G,)
    # observation arrays (a policy may see these through the engine)
    values: np.ndarray  # (N, G, A) value of each analyte if it were measured that day
    measured: np.ndarray  # (N, G, A) the simulator's missingness: False = a test would return nothing
    max_sym: np.ndarray  # (N, G) highest symptom grade that day
    static: np.ndarray  # (N, 6) stage 1-4, tnbc, her2, er, pr, age
    # environment and truth (imaging, labels, endpoints only)
    burden: np.ndarray  # (N, G) sum of the five latent burden compartments
    has_rec: np.ndarray  # (N,) bool
    t_rec: np.ndarray  # (N,) day of true clinical recurrence, nan if none
    comp_day: np.ndarray  # (N,) competing event day, inf if none
    t_det_idx: np.ndarray  # (N,) first grid index with burden >= 12, G if never
    sym3_idx: np.ndarray  # (N,) first grid index with symptom grade >= 3, G if never
    patient_ids: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(self.values.shape[0])

    @property
    def g(self) -> int:
        return int(self.values.shape[1])


def build_world(generator: GeneratorType | str, seed: int, n_generated: int) -> DenseWorld:
    """Generate ``n_generated`` patients and keep the eligible ones (PREREG section 3)."""
    gen = get_generator(generator, seed=seed)
    days = grid_days()
    day_list = [float(d) for d in days]
    vals, meas, sym, burden, static = [], [], [], [], []
    has_rec, t_rec, comp_day, ids = [], [], [], []
    n_comp, n_early = 0, 0
    for i in range(1, n_generated + 1):
        pt = gen.sample_nigerian_baseline(i)
        cd = float(pt.competing_event_day) if pt.competing_event_day is not None else float("inf")
        if cd < GRID_START:
            n_comp += 1
            continue
        if pt.true_recurrence_event and pt.true_recurrence_day is not None and pt.true_recurrence_day < ELIGIBLE_MIN_RECURRENCE_DAY:
            n_early += 1
            continue
        traj, masks, lats = gen.simulate_longitudinal_trajectory(pt, day_list)
        v = np.empty((N_GRID, len(ANALYTES)))
        m = np.empty((N_GRID, len(ANALYTES)), dtype=bool)
        s = np.empty(N_GRID, dtype=np.int8)
        b = np.empty(N_GRID)
        for k, (d, tr, mk, lat) in enumerate(zip(day_list, traj, masks, lats)):
            for j, a in enumerate(ANALYTES):
                v[k, j] = float(tr[a])
                m[k, j] = bool(mk.get(a, True))
            s[k] = max(gen.generate_symptoms(pt, d, lat).values())
            b[k] = lat.b_loc + lat.b_bone + lat.b_liver + lat.b_lung + lat.b_brain
        vals.append(v)
        meas.append(m)
        sym.append(s)
        burden.append(b)
        static.append(
            [
                float(_STAGE[pt.stage]),
                float(pt.subtype == BreastCancerSubtype.TNBC),
                float(pt.her2_status),
                float(pt.er_status),
                float(pt.pr_status),
                float(pt.age),
            ]
        )
        rec = bool(pt.true_recurrence_event and pt.true_recurrence_day is not None)
        has_rec.append(rec)
        t_rec.append(float(pt.true_recurrence_day) if rec else float("nan"))
        comp_day.append(cd)
        ids.append(pt.patient_id)
    burden_a = np.array(burden)
    sym_a = np.array(sym)
    det = np.where((burden_a >= BURDEN_DETECTABLE).any(axis=1), (burden_a >= BURDEN_DETECTABLE).argmax(axis=1), N_GRID)
    s3 = np.where((sym_a >= SYMPTOM_PRESENTATION_GRADE).any(axis=1), (sym_a >= SYMPTOM_PRESENTATION_GRADE).argmax(axis=1), N_GRID)
    return DenseWorld(
        generator=str(GeneratorType(generator).value),
        seed=int(seed),
        day=days,
        values=np.array(vals),
        measured=np.array(meas),
        max_sym=sym_a,
        static=np.array(static),
        burden=burden_a,
        has_rec=np.array(has_rec, dtype=bool),
        t_rec=np.array(t_rec),
        comp_day=np.array(comp_day),
        t_det_idx=det.astype(int),
        sym3_idx=s3.astype(int),
        patient_ids=ids,
        meta={
            "n_generated": int(n_generated),
            "n_eligible": len(ids),
            "n_excluded_competing_before_start": n_comp,
            "n_excluded_recurrence_before_day_210": n_early,
        },
    )
