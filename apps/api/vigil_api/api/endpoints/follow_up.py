"""API Endpoints for Follow-Up Guardian (M6) Task State Machine and Outreach."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_api.audit import record_audit_event
from vigil_api.auth import require_roles
from vigil_api.database import get_db
from vigil_api.guardian import (
    InvalidStateTransitionError,
    get_outreach_list,
    transition_task,
)
from vigil_api.models.v2 import FollowUpTask, ReminderReceipt, User, UserRole
from vigil_api.reminders import run_reminder_cycle
from vigil_api.schemas.v2 import FollowUpTaskResponse, FollowUpTransitionRequest

router = APIRouter()


def _parse_simulated_clock(simulated_now: Optional[str]) -> datetime:
    if not simulated_now:
        return datetime.now(timezone.utc)
    # Handle space in place of + from URL unquoting
    cleaned = simulated_now.replace(" ", "+")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.get(
    "/outreach",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Export prioritized outreach list for clinic staff",
)
def get_prioritized_outreach_list(
    facility_id: Optional[str] = Query(None, description="Optional facility ID filter"),
    simulated_now: Optional[str] = Query(None, description="Injectable clock timestamp for evaluation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.QUALITY_LEAD, UserRole.ADMIN)),
):
    """Retrieve prioritized list of patients due or overdue for surveillance follow-up.

    Supports injectable simulated clock for deterministic testing and escalation checking.
    """
    clock = _parse_simulated_clock(simulated_now)
    outreach = get_outreach_list(db=db, current_time=clock, facility_id=facility_id)
    return outreach


@router.post(
    "/{task_id}/transition",
    response_model=FollowUpTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Transition follow-up task status in state machine",
)
def transition_follow_up_task(
    task_id: str,
    payload: FollowUpTransitionRequest,
    simulated_now: Optional[str] = Query(None, description="Injectable clock timestamp"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.QUALITY_LEAD)),
):
    """Transitions a FollowUpTask to a new status (e.g. completed, declined_with_reason).

    Enforces terminal absorbing state invariant.
    """
    clock = _parse_simulated_clock(simulated_now)

    task = db.execute(select(FollowUpTask).where(FollowUpTask.id == task_id)).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up task '{task_id}' not found.")

    try:
        updated_task = transition_task(
            task=task,
            target_status=payload.target_status,
            reason=payload.reason,
            current_time=clock,
        )
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="follow_up.transition",
        resource_type="follow_up_task",
        resource_id=task.id,
        details={
            "target_status": payload.target_status,
            "reason": payload.reason,
            "patient_id": task.patient_id,
        },
        timestamp=clock,
    )

    db.commit()

    return FollowUpTaskResponse(
        task_id=updated_task.id,
        patient_id=updated_task.patient_id,
        task_type=updated_task.task_type,
        status=updated_task.status,
        due_date=updated_task.due_date,
        escalation_level=updated_task.escalation_level,
        notes=updated_task.notes,
        synthetic=True,
    )


@router.post(
    "/reminders/run",
    status_code=status.HTTP_200_OK,
    summary="Execute reminder worker cycle using injectable clock",
)
def trigger_reminder_cycle(
    simulated_now: Optional[str] = Query(None, description="Injectable clock timestamp"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)),
):
    """Executes a reminder evaluation cycle for active follow-up tasks."""
    clock = _parse_simulated_clock(simulated_now)
    receipts = run_reminder_cycle(db=db, current_time=clock)
    return {
        "status": "completed",
        "evaluated_at": clock.isoformat(),
        "dispatched_count": len(receipts),
        "receipts": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "patient_id": r.patient_id,
                "status": r.status,
                "retry_count": r.retry_count,
                "channel": r.channel,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in receipts
        ],
    }


@router.get(
    "/reminders/receipts",
    status_code=status.HTTP_200_OK,
    summary="List reminder delivery receipts",
)
def list_reminder_receipts(
    patient_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)),
):
    """Retrieve reminder delivery receipts with delivery status and retry history."""
    query = select(ReminderReceipt).order_by(ReminderReceipt.created_at.desc())
    if patient_id:
        query = query.where(ReminderReceipt.patient_id == patient_id)
    if task_id:
        query = query.where(ReminderReceipt.task_id == task_id)

    receipts = db.execute(query).scalars().all()
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "patient_id": r.patient_id,
            "channel": r.channel,
            "recipient": r.recipient,
            "message_text": r.message_text,
            "status": r.status,
            "retry_count": r.retry_count,
            "external_message_id": r.external_message_id,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
        }
        for r in receipts
    ]

