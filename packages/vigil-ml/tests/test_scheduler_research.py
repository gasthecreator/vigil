"""Invariants of the research CP-SAT scheduler (EXP-M7-001 PREREG §8).

These tests are written against the pre-registered hypotheses, not against a result.
"""

from __future__ import annotations

import itertools
import random

import pytest
from vigil_ml.continuity import ClinicalContext, ContinuityHarmModel
from vigil_ml.scheduler import MachineConfig, PatientCourse
from vigil_ml.scheduler_research import (
    ATTEMPTS,
    ResearchConfig,
    ResearchRadiotherapyScheduler,
)

CTX = [c.value for c in ClinicalContext]


def _random_instance(seed: int):
    rng = random.Random(seed)
    n_m = rng.choice([1, 2])
    machines = [
        MachineConfig(
            f"M{i}",
            f"Linac {i}",
            daily_capacity=rng.choice([1, 2]),
            down_days=[d for d in range(3) if rng.random() < 0.25],
        )
        for i in range(n_m)
    ]
    patients = []
    for i in range(rng.choice([3, 4])):
        total = rng.choice([1, 2, 3])
        done = rng.choice([0, 0, 1]) if total > 1 else 0
        patients.append(
            PatientCourse(
                f"P{i}",
                rng.choice(CTX),
                fractions_total=total,
                fractions_completed=done,
                elapsed_delay_days=rng.randint(0, 60),
            )
        )
    return machines, patients


@pytest.fixture(scope="module")
def sched():
    return ResearchRadiotherapyScheduler(
        ContinuityHarmModel(), ResearchConfig("test", window_days=3, max_deterministic_time=5.0)
    )


@pytest.mark.parametrize("seed", range(25))
def test_hard_continuity_never_skips_in_progress_course_when_capacity_is_available(sched, seed):
    machines, patients = _random_instance(seed)
    H = 3
    res = sched.solve(machines, patients, horizon_days=H)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    cap = [sum(0 if d in m.down_days else m.daily_capacity for m in machines) for d in range(H)]
    ongoing = [p for p in patients if p.fractions_completed > 0]
    for p in ongoing:
        remaining = p.fractions_total - p.fractions_completed
        done = 0
        for d in range(H):
            treated = {a.patient_id for a in res.allocations if a.day == d}
            if done >= remaining:
                break
            if p.patient_id in treated:
                done += 1
                continue
            ongoing_treated = sum(1 for q in ongoing if q.patient_id in treated)
            assert ongoing_treated == cap[d], (
                f"seed {seed}: ongoing {p.patient_id} skipped on day {d} although capacity "
                f"{cap[d]} was not exhausted by in-progress courses ({ongoing_treated})"
            )


@pytest.mark.parametrize("seed", range(25))
def test_objective_matches_independent_recomputation_and_warm_start_bound(sched, seed):
    machines, patients = _random_instance(seed)
    H = 3
    res = sched.solve(machines, patients, horizon_days=H)
    recomputed = sched.evaluate_objective(machines, patients, res.allocations, H)
    assert res.solver_objective == pytest.approx(recomputed, abs=0.5)
    # warm start from the urgency ranking: the result can never be worse in the model objective
    assert res.solver_objective <= sched.last_diagnostics["warm_start_objective"] + 0.5


def _brute_force_optimum(sched, machines, patients, H):
    cap = [sum(0 if d in m.down_days else m.daily_capacity for m in machines) for d in range(H)]
    n = len(patients)
    best = None
    day_choices = []
    for d in range(H):
        opts = []
        for r in range(0, min(cap[d], n) + 1):
            opts.extend(itertools.combinations(range(n), r))
        day_choices.append(opts)
    from vigil_ml.scheduler import SlotAllocation

    for plan in itertools.product(*day_choices):
        # per-course fraction budget
        counts = [0] * n
        for day in plan:
            for i in day:
                counts[i] += 1
        if any(counts[i] > patients[i].fractions_total - patients[i].fractions_completed for i in range(n)):
            continue
        # H-i
        ok = True
        for i, p in enumerate(patients):
            if p.fractions_completed == 0:
                continue
            remaining = p.fractions_total - p.fractions_completed
            done = 0
            for d in range(H):
                if done >= remaining:
                    break
                if i in plan[d]:
                    done += 1
                else:
                    on = sum(1 for j, q in enumerate(patients) if q.fractions_completed > 0 and j in plan[d])
                    if on != cap[d]:
                        ok = False
        if not ok:
            continue
        allocs = [
            SlotAllocation(patients[i].patient_id, d, "M0", 0, None)
            for d, day in enumerate(plan)
            for i in day
        ]
        val = sched.evaluate_objective(machines, patients, allocs, H)
        best = val if best is None else min(best, val)
    return best


@pytest.mark.parametrize("seed", range(10))
def test_solver_optimum_equals_brute_force_on_tiny_instances(sched, seed):
    machines, patients = _random_instance(100 + seed)
    H = 3
    res = sched.solve(machines, patients, horizon_days=H)
    assert res.status == "OPTIMAL"
    assert res.solver_objective == pytest.approx(_brute_force_optimum(sched, machines, patients, H), abs=0.5)


def test_objective_contains_no_reward_or_switching_terms():
    """Slack capacity: every course is treated on every possible day; objective has no throughput reward,
    so the only costs are waiting harm before the first fraction and skipped days."""
    sched = ResearchRadiotherapyScheduler(
        ContinuityHarmModel(), ResearchConfig("t", window_days=4, max_deterministic_time=5.0)
    )
    machines = [MachineConfig("M0", "L", daily_capacity=10)]
    pts = [
        PatientCourse("a", ClinicalContext.CURATIVE_TNBC.value, 3, fractions_completed=1, current_machine_id="M9"),
        PatientCourse("b", ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value, 3, elapsed_delay_days=5),
    ]
    res = sched.solve(machines, pts, horizon_days=4)
    assert res.solver_objective == 0  # nothing waits (start day 0), nothing skipped
    # A different current machine than the one available must not be penalised (no switching term).
    assert {a.machine_id for a in res.allocations} == {"M0"}


def test_attempt_registry_matches_preregistration():
    assert {k: (v.window_days, v.max_deterministic_time) for k, v in ATTEMPTS.items()} == {
        "A1": (7, 0.5),
        "A2": (14, 2.0),
        "A3": (30, 2.0),
    }


class _WaitDominatesHarmModel(ContinuityHarmModel):
    """Counterfactual harm model in which waiting is far costlier than a skipped day.

    With the real harm model the harm-only objective already makes skipping an in-progress
    course unattractive (skip penalty 0.01-0.04/day vs waiting 0.0000-0.004/day), so H-i is
    nearly implied by H-ii. This model makes H-i *binding* so the test can fail if H-i is lost.
    """

    def marginal_harm(self, context_str, delay_days, interruption_days=0):  # noqa: ARG002
        return 5.0 if context_str == ClinicalContext.PALLIATIVE_BONE_BRAIN.value else 0.0


def test_hard_continuity_is_binding_when_waiting_is_costlier_than_skipping():
    sched = ResearchRadiotherapyScheduler(
        _WaitDominatesHarmModel(), ResearchConfig("t", window_days=3, max_deterministic_time=5.0)
    )
    machines = [MachineConfig("M0", "L", daily_capacity=1)]
    pts = [
        PatientCourse("ongoing", ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value, 3, fractions_completed=1),
        PatientCourse("pal", ClinicalContext.PALLIATIVE_BONE_BRAIN.value, 1),
    ]
    res = sched.solve(machines, pts, horizon_days=3)
    by_day = {a.day: a.patient_id for a in res.allocations}
    # The in-progress course is treated on its two remaining days first; palliative waits.
    assert by_day[0] == "ongoing" and by_day[1] == "ongoing"
    assert by_day.get(2) == "pal"
