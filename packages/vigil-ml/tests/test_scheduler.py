"""Unit and Property Tests for Radiotherapy Treatment Continuity Scheduler (M7).

Verifies Master Plan §6.7, §10, and §11:
1. Operational capacity and downtime constraints.
2. Palliative acute prioritization vs low-urgency adjuvant cases.
3. No-starvation constraint (W_max).
4. Subgroup equity and absence of wealth bias.
5. Idempotence and reproducibility.
6. Benchmark comparison: HarmAware vs FCFS vs Urgency Heuristic.
7. Brute-force verification on small combinatorial instance.
"""

import pytest
from vigil_ml.continuity import ClinicalContext, ContinuityHarmModel
from vigil_ml.scheduler import (
    MachineConfig,
    PatientCourse,
    RadiotherapyScheduler,
)


@pytest.fixture
def scheduler():
    return RadiotherapyScheduler(ContinuityHarmModel(), max_fairness_disparity_days=5)


def test_downtime_and_capacity_constraints(scheduler):
    """Verifies that machine capacity is respected and down days have zero allocations."""
    machines = [
        MachineConfig(
            machine_id="LINAC-01",
            name="Varian Clinac",
            daily_capacity=2,
            status="active",
            down_days=[1],
        ),
        MachineConfig(
            machine_id="LINAC-02", name="Elekta Synergy", daily_capacity=2, status="down"
        ),
    ]
    patients = [
        PatientCourse(
            patient_id=f"P{i}",
            clinical_context="adjuvant_post_lumpectomy",
            fractions_total=3,
            elapsed_delay_days=65,
        )
        for i in range(4)
    ]

    res = scheduler.solve(machines, patients, horizon_days=4)
    assert res.status in ("OPTIMAL", "FEASIBLE")

    # LINAC-02 is down -> 0 allocations
    assert all(a.machine_id != "LINAC-02" for a in res.allocations)

    # LINAC-01 is down on day 1 -> 0 allocations on day 1
    day_1_allocs = [a for a in res.allocations if a.day == 1]
    assert len(day_1_allocs) == 0

    # Max 2 slots per day on LINAC-01
    for d in range(4):
        d_allocs = [a for a in res.allocations if a.day == d and a.machine_id == "LINAC-01"]
        assert len(d_allocs) <= 2


def test_palliative_prioritization_over_adjuvant(scheduler):
    """Acute palliative metastases must be prioritized over stable post-lumpectomy adjuvant cases."""
    machines = [
        MachineConfig(machine_id="LINAC-01", name="Main Linac", daily_capacity=1, status="active"),
    ]
    # Capacity 1 slot/day. 2 patients competing for day 0:
    # P_pal: acute bone/brain metastasis (delay = 3d, 0 grace period)
    # P_adj: post-lumpectomy (delay = 20d, within 56d grace period)
    patients = [
        PatientCourse(
            patient_id="P_adj",
            clinical_context=ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value,
            fractions_total=1,
            elapsed_delay_days=20,
        ),
        PatientCourse(
            patient_id="P_pal",
            clinical_context=ClinicalContext.PALLIATIVE_BONE_BRAIN.value,
            fractions_total=1,
            elapsed_delay_days=3,
            urgency_bound_days=0,
        ),
    ]

    res = scheduler.solve(machines, patients, horizon_days=3)
    assert res.status in ("OPTIMAL", "FEASIBLE")

    # P_pal must start on day 0
    assert res.patient_start_days["P_pal"] == 0
    # P_adj scheduled on day 1
    assert res.patient_start_days["P_adj"] == 1


def test_no_starvation_w_max_invariant(scheduler):
    """Lower-urgency patients must not be starved indefinitely when W_max is enforced."""
    machines = [
        MachineConfig(machine_id="LINAC-01", name="Main Linac", daily_capacity=1, status="active"),
    ]
    # Single slot per day. Two patients with W_max bounds.
    patients = [
        PatientCourse(
            patient_id="P1",
            clinical_context=ClinicalContext.CURATIVE_TNBC.value,
            fractions_total=1,
            elapsed_delay_days=45,
            max_wait_days=1,
        ),
        PatientCourse(
            patient_id="P2",
            clinical_context=ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value,
            fractions_total=1,
            elapsed_delay_days=25,
            max_wait_days=2,
        ),
    ]

    res = scheduler.solve(machines, patients, horizon_days=3)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    assert res.patient_start_days["P1"] is not None and res.patient_start_days["P1"] <= 1
    assert res.patient_start_days["P2"] is not None and res.patient_start_days["P2"] <= 2


def test_subgroup_fairness_disparity_bound(scheduler):
    """Asserts that wait disparities across demographic/geographic subgroups remain bounded."""
    machines = [
        MachineConfig(machine_id="LINAC-01", name="Linac", daily_capacity=2, status="active"),
    ]
    # 4 patients: 2 rural_public, 2 urban_referral
    patients = [
        PatientCourse(
            "P_r1",
            ClinicalContext.CURATIVE_TNBC.value,
            fractions_total=1,
            elapsed_delay_days=30,
            subgroup="rural_public",
        ),
        PatientCourse(
            "P_r2",
            ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value,
            fractions_total=1,
            elapsed_delay_days=30,
            subgroup="rural_public",
        ),
        PatientCourse(
            "P_u1",
            ClinicalContext.CURATIVE_TNBC.value,
            fractions_total=1,
            elapsed_delay_days=30,
            subgroup="urban_referral",
        ),
        PatientCourse(
            "P_u2",
            ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value,
            fractions_total=1,
            elapsed_delay_days=30,
            subgroup="urban_referral",
        ),
    ]

    res = scheduler.solve(machines, patients, horizon_days=5)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    assert res.subgroup_disparity_days <= 5.0
    assert res.is_fairness_certified is True


def test_idempotence_and_reproducibility(scheduler):
    """Re-running the solver on identical inputs produces identical slot assignments."""
    machines = [
        MachineConfig(machine_id="M1", name="Linac 1", daily_capacity=2, status="active"),
    ]
    patients = [
        PatientCourse(
            "P1", ClinicalContext.CURATIVE_TNBC.value, fractions_total=2, elapsed_delay_days=50
        ),
        PatientCourse(
            "P2",
            ClinicalContext.ADJUVANT_POST_MASTECTOMY.value,
            fractions_total=2,
            elapsed_delay_days=60,
        ),
    ]

    run1 = scheduler.solve(machines, patients, horizon_days=5)
    run2 = scheduler.solve(machines, patients, horizon_days=5)

    assert run1.status == run2.status
    assert run1.total_expected_harm == run2.total_expected_harm
    assert run1.patient_start_days == run2.patient_start_days
    assert len(run1.allocations) == len(run2.allocations)


def test_harm_aware_vs_fcfs_comparison(scheduler):
    """HarmAware scheduler achieves lower or equal total harm compared to naive FCFS queue."""
    machines = [
        MachineConfig(machine_id="M1", name="Linac 1", daily_capacity=1, status="active"),
    ]
    # Patient A arrived 40 days ago (Lumpectomy, still within 56d grace period -> 0 excess harm)
    # Patient B arrived 20 days ago (TNBC, rapid doubling, past 6-week grace period -> high harm)
    # FCFS schedules A first, harming B. HarmAware schedules B first.
    patients = [
        PatientCourse(
            "P_lump",
            ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value,
            fractions_total=2,
            elapsed_delay_days=40,
        ),
        PatientCourse(
            "P_tnbc", ClinicalContext.CURATIVE_TNBC.value, fractions_total=2, elapsed_delay_days=50
        ),
    ]

    res_opt = scheduler.solve(machines, patients, horizon_days=5)
    res_fcfs = scheduler.solve_fcfs(machines, patients, horizon_days=5)

    assert res_opt.total_expected_harm <= res_fcfs.total_expected_harm


def test_brute_force_optimality_on_minimal_instance():
    """Verifies that CP-SAT solution matches exhaustive brute-force search on small instance."""
    harm_model = ContinuityHarmModel()
    machines = [MachineConfig("M1", "Linac", daily_capacity=1, status="active")]
    p_pal = PatientCourse(
        "P_pal",
        ClinicalContext.PALLIATIVE_BONE_BRAIN.value,
        fractions_total=1,
        elapsed_delay_days=5,
    )
    p_lump = PatientCourse(
        "P_lump",
        ClinicalContext.ADJUVANT_POST_LUMPECTOMY.value,
        fractions_total=1,
        elapsed_delay_days=20,
    )

    # Brute-force evaluation of the 2 possible permutation assignments:
    # Option 1: P_pal on day 0, P_lump on day 1
    harm_opt1 = (
        harm_model.compute_harm(p_pal.clinical_context, 5 + 0).expected_harm
        + harm_model.compute_harm(p_lump.clinical_context, 20 + 1).expected_harm
    )

    # Option 2: P_lump on day 0, P_pal on day 1
    harm_opt2 = (
        harm_model.compute_harm(p_lump.clinical_context, 20 + 0).expected_harm
        + harm_model.compute_harm(p_pal.clinical_context, 5 + 1).expected_harm
    )

    assert harm_opt1 < harm_opt2, (
        f"Option 1 ({harm_opt1}) should be strictly better than Option 2 ({harm_opt2})"
    )

    scheduler = RadiotherapyScheduler(harm_model)
    res = scheduler.solve(machines, [p_pal, p_lump], horizon_days=2)

    assert res.patient_start_days["P_pal"] == 0
    assert res.patient_start_days["P_lump"] == 1
    assert round(res.total_expected_harm, 4) == round(harm_opt1, 4)


# ---------------------------------------------------------------------------
# ADR-0019: explainable urgency ranking (shipped M7 recommendation)
# ---------------------------------------------------------------------------


def _mixed_cohort():
    ctx = ClinicalContext
    return [
        PatientCourse("ongoing", ctx.ADJUVANT_POST_LUMPECTOMY.value, 15, fractions_completed=3, elapsed_delay_days=5),
        PatientCourse("pal", ctx.PALLIATIVE_BONE_BRAIN.value, 5, elapsed_delay_days=2),
        PatientCourse("tnbc", ctx.CURATIVE_TNBC.value, 25, elapsed_delay_days=40),
        PatientCourse("lump_old", ctx.ADJUVANT_POST_LUMPECTOMY.value, 15, elapsed_delay_days=60),
        PatientCourse("lump_flagged", ctx.ADJUVANT_POST_LUMPECTOMY.value, 15, elapsed_delay_days=1, urgency_bound_days=7),
    ]


def test_rank_urgency_order_and_reasons(scheduler):
    machines = [MachineConfig("M1", "Linac 1", daily_capacity=2)]
    out = scheduler.rank_urgency(machines, _mixed_cohort(), horizon_days=3)
    order = sorted(out.ranks, key=out.ranks.get)
    assert order == ["ongoing", "lump_flagged", "pal", "tnbc", "lump_old"]
    assert "course in progress" in out.rank_reasons["ongoing"]
    assert "clinician-flagged" in out.rank_reasons["lump_flagged"]
    # capacity 2/day: the two highest-priority courses are treated on day 0, nobody else
    day0 = {a.patient_id for a in out.schedule.allocations if a.day == 0}
    assert day0 == {"ongoing", "lump_flagged"}
    assert out.schedule.is_fairness_certified is False


def test_rank_urgency_equals_frozen_study_arm_without_flags(scheduler):
    """The shipped ranking must not silently differ from the pre-registered study arm."""
    machines = [MachineConfig("M1", "Linac 1", daily_capacity=2)]
    cohort = [p for p in _mixed_cohort() if p.patient_id != "lump_flagged"]
    a = scheduler.rank_urgency(machines, cohort, horizon_days=6).schedule
    b = scheduler.solve_urgency_heuristic(machines, cohort, horizon_days=6)
    key = lambda r: sorted((x.patient_id, x.day, x.machine_id) for x in r.allocations)  # noqa: E731
    assert key(a) == key(b)


def test_fairness_certification_is_not_a_constant():
    """cp-sat: certified only when a bound was imposed; greedy policies never certify."""
    machines = [MachineConfig("M1", "Linac 1", daily_capacity=1)]
    pts = [
        PatientCourse("a", ClinicalContext.CURATIVE_TNBC.value, 1, subgroup="x"),
        PatientCourse("b", ClinicalContext.CURATIVE_TNBC.value, 1, subgroup="y"),
    ]
    unbounded = RadiotherapyScheduler(ContinuityHarmModel())
    assert unbounded.solve(machines, pts, horizon_days=3).is_fairness_certified is False
    assert unbounded.solve_fcfs(machines, pts, horizon_days=3).is_fairness_certified is False
    assert unbounded.solve_urgency_heuristic(machines, pts, horizon_days=3).is_fairness_certified is False
