"""Research CP-SAT scheduler for experiment EXP-M7-001 (research track, NOT shipped).

Implements exactly the three structural hypotheses pre-registered in
``experiments/EXP-M7-001/PREREG.md``:

* H-i   hard continuity: an in-progress course may be skipped on a day only if the
        day's whole capacity is used by other in-progress courses;
* H-ii  harm-only objective (harm-model units only: waiting harm of not-yet-started
        courses, skipped-day harm of in-progress courses; no rewards, no switching or
        idle penalties, no day-decay);
* H-iii rolling horizon with a warm start from the urgency ranking's allocation.

Hard constraints besides H-i are machine capacity and downtime. Fairness bounds,
starvation ceilings and clinician urgency bounds are deliberately NOT part of this
arm (they are separate questions); the shipped API therefore never uses this class.

Determinism: single worker, ``max_deterministic_time`` budget (machine-speed independent
for a fixed OR-Tools version), fixed random seed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from vigil_ml.continuity import ContinuityHarmModel
from vigil_ml.scheduler import (
    CPSAT_VALIDATION_STATUS,
    MachineConfig,
    PatientCourse,
    RadiotherapyScheduler,
    ScheduleResult,
    SlotAllocation,
    _course_uid,
)

COST_SCALE = 1_000_000  # harm (a probability-like quantity) -> integer cost


@dataclass(frozen=True)
class ResearchConfig:
    """One pre-registered attempt (A1/A2/A3 in the PREREG)."""

    name: str
    window_days: int
    max_deterministic_time: float
    wall_limit_seconds: float = 20.0


ATTEMPTS: Dict[str, ResearchConfig] = {
    "A1": ResearchConfig("A1", window_days=7, max_deterministic_time=0.5),
    "A2": ResearchConfig("A2", window_days=14, max_deterministic_time=2.0),
    "A3": ResearchConfig("A3", window_days=30, max_deterministic_time=2.0),
}


def _capacity(m: MachineConfig, d: int) -> int:
    return 0 if (m.status == "down" or d in m.down_days) else m.daily_capacity


class ResearchRadiotherapyScheduler:
    """Harm-only CP-SAT with hard continuity and an urgency-ranking warm start."""

    def __init__(
        self,
        harm_model: Optional[ContinuityHarmModel] = None,
        config: ResearchConfig = ATTEMPTS["A1"],
    ):
        self.harm_model = harm_model or ContinuityHarmModel()
        self.config = config
        self.last_diagnostics: Dict[str, object] = {}

    # -- costs (single source of truth, also used by the independent evaluator) ----------
    def wait_cost(self, p: PatientCourse, d: int) -> int:
        """Cost of course ``p`` still waiting (not started) on window day ``d``."""
        return int(
            round(
                COST_SCALE
                * self.harm_model.marginal_harm(p.clinical_context, p.elapsed_delay_days + d, 1)
            )
        )

    def skip_cost(self, p: PatientCourse) -> int:
        """Cost of one skipped day of an in-progress course."""
        pen = self.harm_model.get_parameters(p.clinical_context).interruption_daily_penalty
        return int(round(COST_SCALE * pen))

    def evaluate_objective(
        self,
        machines: List[MachineConfig],
        patients: List[PatientCourse],
        allocations: List[SlotAllocation],
        horizon_days: int,
    ) -> int:
        """Objective of an allocation, recomputed in plain Python (independent of CP-SAT)."""
        treated: Dict[Tuple[str, int], int] = {}
        for a in allocations:
            key = (a.course_id or a.patient_id, a.day)
            treated[key] = treated.get(key, 0) + 1
        total = 0
        for p in patients:
            uid = _course_uid(p)
            remaining = max(0, p.fractions_total - p.fractions_completed)
            if p.fractions_completed == 0:
                started = False
                for d in range(horizon_days):
                    if treated.get((uid, d), 0) > 0:
                        started = True
                    if not started:
                        total += self.wait_cost(p, d)
            else:
                done = 0
                for d in range(horizon_days):
                    if done < remaining:
                        if treated.get((uid, d), 0) > 0:
                            done += 1
                        else:
                            total += self.skip_cost(p)
        return total

    # -- model ---------------------------------------------------------------------------
    def solve(
        self,
        machines: List[MachineConfig],
        patients: List[PatientCourse],
        horizon_days: int = 7,
        max_time_in_seconds: Optional[float] = None,  # accepted for interface parity; ignored
    ) -> ScheduleResult:
        t0 = time.perf_counter()
        n_days = max(1, horizon_days)
        model = cp_model.CpModel()
        uids = [_course_uid(p) for p in patients]

        x: Dict[Tuple[str, int, str], cp_model.IntVar] = {}
        y: Dict[Tuple[str, int], cp_model.IntVar] = {}
        for p, uid in zip(patients, uids):
            for d in range(n_days):
                vs = []
                for m in machines:
                    v = model.NewBoolVar(f"x_{uid}_{d}_{m.machine_id}")
                    x[(uid, d, m.machine_id)] = v
                    vs.append(v)
                yv = model.NewBoolVar(f"y_{uid}_{d}")
                y[(uid, d)] = yv
                model.Add(sum(vs) == yv)

        # capacity / downtime (hard)
        cap_day = [sum(_capacity(m, d) for m in machines) for d in range(n_days)]
        for m in machines:
            for d in range(n_days):
                model.Add(sum(x[(uid, d, m.machine_id)] for uid in uids) <= _capacity(m, d))

        # at most the remaining fractions
        for p, uid in zip(patients, uids):
            remaining = max(0, p.fractions_total - p.fractions_completed)
            model.Add(sum(y[(uid, d)] for d in range(n_days)) <= remaining)

        objective: List = []
        started: Dict[Tuple[str, int], cp_model.IntVar] = {}
        skip: Dict[Tuple[str, int], cp_model.IntVar] = {}
        active: Dict[Tuple[str, int], cp_model.IntVar] = {}

        ongoing = [(p, uid) for p, uid in zip(patients, uids) if p.fractions_completed > 0]
        ongoing_uids = [uid for _, uid in ongoing]

        for p, uid in zip(patients, uids):
            if p.fractions_completed == 0:
                prev = None
                for d in range(n_days):
                    st = model.NewBoolVar(f"started_{uid}_{d}")
                    started[(uid, d)] = st
                    model.Add(y[(uid, d)] <= st)
                    if prev is None:
                        model.Add(st == y[(uid, 0)])
                    else:
                        model.Add(st >= prev)
                        model.Add(st <= prev + y[(uid, d)])
                    prev = st
                    objective.append(self.wait_cost(p, d) * (1 - st))
            else:
                remaining = p.fractions_total - p.fractions_completed
                sk_cost = self.skip_cost(p)
                for d in range(n_days):
                    c = sum(y[(uid, dd)] for dd in range(d))  # fractions delivered before d
                    act = model.NewBoolVar(f"active_{uid}_{d}")
                    active[(uid, d)] = act
                    model.Add(c <= remaining - 1).OnlyEnforceIf(act)
                    model.Add(c >= remaining).OnlyEnforceIf(act.Not())
                    sk = model.NewBoolVar(f"skip_{uid}_{d}")
                    skip[(uid, d)] = sk
                    model.Add(sk >= act - y[(uid, d)])
                    model.Add(sk <= act)
                    model.Add(sk + y[(uid, d)] <= 1)
                    objective.append(sk_cost * sk)
                    # H-i: a skip is allowed only if in-progress courses fill the day's capacity
                    ongoing_today = sum(y[(u, d)] for u in ongoing_uids)
                    model.Add(ongoing_today >= cap_day[d]).OnlyEnforceIf(sk)

        model.Minimize(sum(objective))

        # warm start from the urgency ranking on the same window (H-iii)
        warm = RadiotherapyScheduler(self.harm_model).solve_urgency_heuristic(
            machines, patients, horizon_days=n_days
        )
        warm_set = {(a.course_id or a.patient_id, a.day, a.machine_id) for a in warm.allocations}
        for (uid, d, mid), v in x.items():
            model.AddHint(v, 1 if (uid, d, mid) in warm_set else 0)
        warm_obj = self.evaluate_objective(machines, patients, warm.allocations, n_days)

        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1
        solver.parameters.random_seed = 0
        solver.parameters.max_deterministic_time = self.config.max_deterministic_time
        solver.parameters.max_time_in_seconds = self.config.wall_limit_seconds
        status = solver.Solve(model)

        status_str = "INFEASIBLE"
        solver_obj: Optional[float] = None
        if status == cp_model.OPTIMAL:
            status_str = "OPTIMAL"
        elif status == cp_model.FEASIBLE:
            status_str = "FEASIBLE"
        elif status == cp_model.UNKNOWN:
            status_str = "TIMEOUT"

        allocations: List[SlotAllocation] = []
        patient_start: Dict[str, Optional[int]] = {}
        course_start: Dict[str, Optional[int]] = {}
        fr_sched: Dict[str, int] = {}
        if status_str in ("OPTIMAL", "FEASIBLE"):
            solver_obj = float(solver.ObjectiveValue())
            for p, uid in zip(patients, uids):
                cnt = p.fractions_completed
                first: Optional[int] = None
                n = 0
                for d in range(n_days):
                    for m in machines:
                        if solver.Value(x[(uid, d, m.machine_id)]) == 1:
                            cnt += 1
                            n += 1
                            first = d if first is None else first
                            allocations.append(
                                SlotAllocation(p.patient_id, d, m.machine_id, cnt, p.course_id)
                            )
                patient_start[p.patient_id] = first
                if p.course_id:
                    course_start[p.course_id] = first
                fr_sched[p.patient_id] = n
        else:
            for p in patients:
                patient_start[p.patient_id] = None
                if p.course_id:
                    course_start[p.course_id] = None
                fr_sched[p.patient_id] = 0

        self.last_diagnostics = {
            "warm_start_objective": warm_obj,
            "solver_objective": solver_obj,
            "status": status_str,
        }
        return ScheduleResult(
            status=status_str,
            allocations=allocations,
            patient_start_days=patient_start,
            patient_fractions_scheduled=fr_sched,
            total_expected_harm=0.0,  # realised harm is computed by the study, not here
            marginal_explanations={},
            subgroup_mean_waits={},
            subgroup_disparity_days=0.0,
            machine_utilization={},
            solver_wall_time_seconds=round(time.perf_counter() - t0, 4),
            course_start_days=course_start,
            is_fairness_certified=False,
            synthetic=True,
            solver_objective=solver_obj,
            validation_status=CPSAT_VALIDATION_STATUS,
        )
