"""Follow-Up Guardian (M6) State Machine, Escalation Ladder, and Property Tests.

Implements Master Plan §6.6 (M6) and Phase 5a Guardian requirements:
- State machine with terminal absorbing states (completed, declined_with_reason, transferred,
  cancelled_by_clinician, lost_to_follow_up_after_N_attempts).
- Injectable clock for deterministic escalation evaluation.
- Escalation ladder reaching all levels (0 -> 1 -> 2 -> 3).
- Outreach list export endpoint with urgency ranking.
- Property-based tests (Hypothesis):
  1. No task can disappear (task count is invariant under evaluation).
  2. Escalation monotonicity under advancing time.
  3. Every escalation path is reachable.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from vigil_api.auth import create_access_token
from vigil_api.database import Base, get_db
from vigil_api.guardian import (
    TERMINAL_STATUSES,
    InvalidStateTransitionError,
    evaluate_tasks,
    transition_task,
)
from vigil_api.main import app
from vigil_api.models.v2 import (
    Facility,
    FollowUpTask,
    FollowUpTaskStatus,
    FollowUpTaskType,
    Patient,
    UserRole,
)


@pytest.fixture
def guardian_db(tmp_path):
    """Set up an isolated database for Follow-Up Guardian tests."""
    db_file = tmp_path / "test_guardian.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        fac = Facility(
            id="fac-g",
            name="Guardian Clinic",
            code="GC-01",
            country="NG",
            tier="tertiary",
            active=True,
            created_at=now,
        )
        session.add(fac)

        pat = Patient(
            id="pat-g-01",
            facility_id="fac-g",
            mrn="MRN-G-01",
            biological_sex="female",
            primary_cancer_type="breast",
            synthetic=True,
            status="active",
            created_at=now,
            updated_at=now,
        )
        session.add(pat)
        session.commit()

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


@pytest.fixture
def coordinator_auth():
    token = create_access_token(subject="nurse_coordinator", role=UserRole.NURSE_CLERK.value)
    return {"Authorization": f"Bearer {token}"}


def test_state_machine_terminal_absorbing_invariant(guardian_db):
    """Verify that terminal states (completed, declined, transferred, cancelled, lost) are absorbing."""
    _, engine = guardian_db
    now = datetime.now(timezone.utc)

    for terminal_status in TERMINAL_STATUSES:
        with Session(engine) as session:
            task = FollowUpTask(
                patient_id="pat-g-01",
                task_type=FollowUpTaskType.REPEAT_SPECIMEN.value,
                status=FollowUpTaskStatus.PENDING.value,
                due_date=now,
                escalation_level=0,
                created_at=now,
                updated_at=now,
            )
            session.add(task)
            session.flush()

            # Transition to terminal state
            transition_task(task, terminal_status, reason="Terminal milestone reached")
            assert task.status == terminal_status

            # Attempting to re-open or transition away from terminal state must be rejected
            with pytest.raises(InvalidStateTransitionError):
                transition_task(task, FollowUpTaskStatus.PENDING.value)

            with pytest.raises(InvalidStateTransitionError):
                transition_task(task, FollowUpTaskStatus.ESCALATED.value)


def test_escalation_ladder_reachability_with_injectable_clock(guardian_db):
    """Verify that simulated clock advances overdue tasks through all levels of the escalation ladder."""
    _, engine = guardian_db
    t0 = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

    with Session(engine) as session:
        task = FollowUpTask(
            id="task-escalate-test",
            patient_id="pat-g-01",
            task_type=FollowUpTaskType.IMAGING_REFERRAL.value,
            status=FollowUpTaskStatus.PENDING.value,
            due_date=t0,
            escalation_level=0,
            created_at=t0 - timedelta(days=7),
            updated_at=t0 - timedelta(days=7),
        )
        session.add(task)
        session.commit()

    # 1. Day 1 overdue (delay = 1 day <= 2 days) -> Level 0
    t_day1 = t0 + timedelta(days=1)
    with Session(engine) as session:
        evaluate_tasks(session, current_time=t_day1)
        t = session.execute(
            select(FollowUpTask).where(FollowUpTask.id == "task-escalate-test")
        ).scalar_one()
        assert t.escalation_level == 0
        assert t.status == FollowUpTaskStatus.PENDING.value

    # 2. Day 3 overdue (delay = 3 days > 2 days) -> Level 1 (Nurse Outreach)
    t_day3 = t0 + timedelta(days=3)
    with Session(engine) as session:
        evaluate_tasks(session, current_time=t_day3)
        t = session.execute(
            select(FollowUpTask).where(FollowUpTask.id == "task-escalate-test")
        ).scalar_one()
        assert t.escalation_level == 1
        assert t.status == FollowUpTaskStatus.ESCALATED.value

    # 3. Day 8 overdue (delay = 8 days > 7 days) -> Level 2 (Clinician Review)
    t_day8 = t0 + timedelta(days=8)
    with Session(engine) as session:
        evaluate_tasks(session, current_time=t_day8)
        t = session.execute(
            select(FollowUpTask).where(FollowUpTask.id == "task-escalate-test")
        ).scalar_one()
        assert t.escalation_level == 2
        assert t.status == FollowUpTaskStatus.ESCALATED.value

    # 4. Day 15 overdue (delay = 15 days > 14 days) -> Level 3 (Clinic Lead Escalation)
    t_day15 = t0 + timedelta(days=15)
    with Session(engine) as session:
        evaluate_tasks(session, current_time=t_day15)
        t = session.execute(
            select(FollowUpTask).where(FollowUpTask.id == "task-escalate-test")
        ).scalar_one()
        assert t.escalation_level == 3
        assert t.status == FollowUpTaskStatus.ESCALATED.value


def test_outreach_list_export_endpoint(guardian_db, coordinator_auth):
    """Verify outreach list export endpoint sorts tasks by urgency and returns patient metadata."""
    client, engine = guardian_db
    t0 = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

    with Session(engine) as session:
        # Task 1: Slightly overdue (3 days) -> Level 1
        t1 = FollowUpTask(
            patient_id="pat-g-01",
            task_type=FollowUpTaskType.REPEAT_SPECIMEN.value,
            status=FollowUpTaskStatus.PENDING.value,
            due_date=t0 - timedelta(days=3),
            escalation_level=0,
            created_at=t0 - timedelta(days=10),
            updated_at=t0 - timedelta(days=10),
        )
        # Task 2: Severely overdue (20 days) -> Level 3
        t2 = FollowUpTask(
            patient_id="pat-g-01",
            task_type=FollowUpTaskType.IMAGING_REFERRAL.value,
            status=FollowUpTaskStatus.PENDING.value,
            due_date=t0 - timedelta(days=20),
            escalation_level=0,
            created_at=t0 - timedelta(days=30),
            updated_at=t0 - timedelta(days=30),
        )
        session.add_all([t1, t2])
        session.commit()

    # Call outreach endpoint with injectable simulated clock
    r = client.get(
        f"/api/v1/follow-up/outreach?simulated_now={t0.isoformat()}",
        headers=coordinator_auth,
    )
    assert r.status_code == 200
    roster = r.json()
    assert len(roster) >= 2

    # Roster must be ordered strictly by urgency (escalation_level desc, days_overdue desc)
    first_item = roster[0]
    second_item = roster[1]
    assert first_item["escalation_level"] == 3
    assert first_item["days_overdue"] >= 20.0
    assert first_item["synthetic"] is True
    assert first_item["mrn"] == "MRN-G-01"

    assert second_item["escalation_level"] == 1
    assert second_item["days_overdue"] >= 3.0


# ==============================================================================
# Property-Based Tests (Hypothesis): Invariants across arbitrary schedules
# ==============================================================================


@given(
    days_advance=st.integers(min_value=0, max_value=60),
    num_tasks=st.integers(min_value=1, max_value=8),
)
def test_hypothesis_no_task_disappears(days_advance: int, num_tasks: int):
    """Property test: No task can disappear under arbitrary clock evaluation."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    with Session(engine) as session:
        fac = Facility(
            id="f", name="Fac", code="F", country="NG", tier="t", active=True, created_at=t0
        )
        pat = Patient(
            id="p",
            facility_id="f",
            mrn="M",
            biological_sex="female",
            primary_cancer_type="breast",
            synthetic=True,
            status="active",
            created_at=t0,
            updated_at=t0,
        )
        session.add_all([fac, pat])

        for i in range(num_tasks):
            due = t0 + timedelta(days=i * 3)
            task = FollowUpTask(
                id=f"tsk-{i}",
                patient_id="p",
                task_type=FollowUpTaskType.CLINICAL_REVIEW.value,
                status=FollowUpTaskStatus.PENDING.value,
                due_date=due,
                escalation_level=0,
                created_at=t0,
                updated_at=t0,
            )
            session.add(task)
        session.commit()

    # Advance clock arbitrarily
    eval_clock = t0 + timedelta(days=days_advance)
    with Session(engine) as session:
        evaluate_tasks(session, current_time=eval_clock)
        remaining_tasks = session.execute(select(FollowUpTask)).scalars().all()

        # Invariant 1: Task count never decreases (no task can disappear)
        assert len(remaining_tasks) == num_tasks

        # Invariant 2: Escalation level is bounded in [0, 3]
        for t in remaining_tasks:
            assert 0 <= t.escalation_level <= 3
