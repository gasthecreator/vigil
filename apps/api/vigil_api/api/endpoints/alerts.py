"""API Endpoints for Alert Management and Clinician Disposition Acknowledgement."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_api.audit import record_audit_event
from vigil_api.auth import require_roles
from vigil_api.database import get_db
from vigil_api.models.v2 import (
    Alert,
    AlertAcknowledgement,
    AlertDisposition,
    AlertStatus,
    User,
    UserRole,
)
from vigil_api.schemas.v2 import AlertAcknowledgeRequest, AlertAcknowledgeResponse, AlertSummary

router = APIRouter()


@router.get(
    "/",
    response_model=List[AlertSummary],
    status_code=status.HTTP_200_OK,
    summary="List active surveillance alerts",
)
def list_alerts(
    status_filter: str = "open",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.QUALITY_LEAD, UserRole.NURSE_CLERK, UserRole.ADMIN)),
):
    """Retrieve surveillance alerts filtered by status."""
    query = select(Alert).offset(skip).limit(limit)
    if status_filter:
        query = query.where(Alert.status == status_filter)
    alerts = db.execute(query).scalars().all()
    return alerts


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertAcknowledgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge alert with mandatory clinical disposition",
)
def acknowledge_alert(
    alert_id: str,
    payload: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.QUALITY_LEAD)),
):
    """Mandatory acknowledgement disposition for alerts.

    Prevents silent dismissal of clinical alerts per MASTER_PLAN §6.6.
    """
    now = datetime.now(timezone.utc)

    alert = db.execute(select(Alert).where(Alert.id == alert_id)).scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found.")

    # Validate disposition value
    valid_dispositions = {d.value for d in AlertDisposition}
    if payload.disposition not in valid_dispositions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid disposition '{payload.disposition}'. Allowed: {sorted(list(valid_dispositions))}",
        )

    rationale = payload.rationale_text or payload.note or "Clinical disposition recorded"

    ack = AlertAcknowledgement(
        alert_id=alert.id,
        user_id=current_user.id,
        disposition=payload.disposition,
        rationale_text=rationale,
        acknowledged_at=now,
    )
    db.add(ack)

    alert.status = AlertStatus.ACKNOWLEDGED.value
    db.flush()

    # Record audit event
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="alert.acknowledged",
        resource_type="Alert",
        resource_id=alert.id,
        details={
            "disposition": payload.disposition,
            "rationale_text": rationale,
            "patient_id": alert.patient_id,
        },
        timestamp=now,
    )

    db.commit()

    return AlertAcknowledgeResponse(
        alert_id=alert.id,
        status=alert.status,
        disposition=ack.disposition,
        rationale_text=ack.rationale_text,
        acknowledged_at=ack.acknowledged_at,
        acknowledged_by=current_user.id,
        synthetic=True,
    )
