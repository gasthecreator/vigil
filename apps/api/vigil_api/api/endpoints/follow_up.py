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
from vigil_api.models.v2 import FollowUpTask, User, UserRole
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
