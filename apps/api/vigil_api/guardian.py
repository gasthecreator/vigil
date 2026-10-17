"""Module M6: Follow-Up Guardian Engine.

Implements Master Plan §6.6 (M6) and Phase 5a Follow-Up requirements:
- FollowUpTask state machine with terminal states and absorbing invariant.
- Injectable clock for deterministic evaluation and time simulation.
- Escalation ladder (Level 0 -> Level 1 -> Level 2 -> Level 3).
- Outreach list generator for clinic coordinators and nurses.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from vigil_api.models.v2 import (
    FollowUpTask,
    FollowUpTaskStatus,
    Patient,
)

TERMINAL_STATUSES: Set[str] = {
    FollowUpTaskStatus.COMPLETED.value,
    FollowUpTaskStatus.DECLINED_WITH_REASON.value,
    FollowUpTaskStatus.TRANSFERRED.value,
    FollowUpTaskStatus.CANCELLED_BY_CLINICIAN.value,
    FollowUpTaskStatus.LOST_TO_FOLLOW_UP_AFTER_N_ATTEMPTS.value,
    FollowUpTaskStatus.CANCELLED.value,
}

ACTIVE_STATUSES: Set[str] = {
    FollowUpTaskStatus.PENDING.value,
    FollowUpTaskStatus.IN_PROGRESS.value,
    FollowUpTaskStatus.ESCALATED.value,
}


class InvalidStateTransitionError(ValueError):
    """Raised when attempting an invalid transition on a FollowUpTask."""

    pass


def transition_task(
    task: FollowUpTask,
    target_status: FollowUpTaskStatus | str,
    reason: Optional[str] = None,
    current_time: Optional[datetime] = None,
) -> FollowUpTask:
    """Transition a FollowUpTask to a target status with validation of terminal absorption."""
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    target_str = (
        target_status.value if isinstance(target_status, FollowUpTaskStatus) else str(target_status)
    )

    # Invariant: Terminal states are absorbing
    if task.status in TERMINAL_STATUSES:
        raise InvalidStateTransitionError(
            f"Cannot transition task '{task.id}' from terminal state '{task.status}' to '{target_str}'."
        )

    task.status = target_str
    task.updated_at = current_time

    if target_str == FollowUpTaskStatus.COMPLETED.value:
        task.completed_at = current_time

    if reason:
        existing_notes = task.notes or ""
        separator = " | " if existing_notes else ""
        task.notes = (
            f"{existing_notes}{separator}[{current_time.isoformat()}] {target_str}: {reason}"
        )

    return task


def evaluate_tasks(
    db: Session,
    current_time: Optional[datetime] = None,
) -> List[FollowUpTask]:
    """Evaluate active follow-up tasks against the escalation ladder using an injectable clock.

    Escalation rules:
      - delay <= 0: Level 0 (not overdue)
      - delay > 2 days: Level 1 (Nurse Outreach / First Reminder)
      - delay > 7 days: Level 2 (Clinician Review / Second Reminder)
      - delay > 14 days: Level 3 (Clinic Lead Escalation)
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Normalize current_time to tz-aware UTC
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    active_tasks = (
        db.execute(select(FollowUpTask).where(FollowUpTask.status.in_(ACTIVE_STATUSES)))
        .scalars()
        .all()
    )

    updated_tasks: List[FollowUpTask] = []

    for task in active_tasks:
        due = task.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        delay = current_time - due

        if delay > timedelta(days=14):
            new_level = 3
        elif delay > timedelta(days=7):
            new_level = 2
        elif delay > timedelta(days=2):
            new_level = 1
        else:
            new_level = 0

        if new_level > task.escalation_level:
            task.escalation_level = new_level
            task.status = FollowUpTaskStatus.ESCALATED.value
            task.updated_at = current_time
            existing = task.notes or ""
            task.notes = (
                f"{existing} | Escalated to level {new_level} at {current_time.isoformat()}".strip(
                    " | "
                )
            )
            updated_tasks.append(task)
        elif new_level == 0 and task.status == FollowUpTaskStatus.ESCALATED.value:
            # If due date was extended into the future
            task.escalation_level = 0
            task.status = FollowUpTaskStatus.PENDING.value
            task.updated_at = current_time
            updated_tasks.append(task)

    db.flush()
    return updated_tasks


def get_outreach_list(
    db: Session,
    current_time: Optional[datetime] = None,
    facility_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Export the prioritized outreach roster for clinic nurses and coordinators."""
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    # First update escalations
    evaluate_tasks(db, current_time=current_time)

    query = (
        select(FollowUpTask, Patient)
        .join(Patient, FollowUpTask.patient_id == Patient.id)
        .where(FollowUpTask.status.in_(ACTIVE_STATUSES))
    )

    if facility_id:
        query = query.where(Patient.facility_id == facility_id)

    results = db.execute(query).all()

    outreach_items = []
    for task, patient in results:
        due = task.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        days_overdue = max(0.0, (current_time - due).total_seconds() / 86400.0)

        outreach_items.append(
            {
                "task_id": task.id,
                "patient_id": patient.id,
                "facility_id": patient.facility_id,
                "mrn": patient.mrn,
                "synthetic": patient.synthetic,
                "task_type": task.task_type,
                "status": task.status,
                "escalation_level": task.escalation_level,
                "due_date": task.due_date.isoformat(),
                "days_overdue": round(days_overdue, 2),
                "alert_id": task.alert_id,
                "notes": task.notes,
            }
        )

    # Sort by urgency: escalation level desc, days overdue desc
    outreach_items.sort(
        key=lambda x: (x["escalation_level"], x["days_overdue"]),
        reverse=True,
    )
    return outreach_items
