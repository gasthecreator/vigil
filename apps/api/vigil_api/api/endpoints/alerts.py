"""API Endpoints for Alert Management and Clinician Disposition Acknowledgement."""

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_api.audit import record_audit_event
from vigil_api.auth import require_roles
from vigil_api.consent import verify_patient_consent
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
    current_user: User = Depends(
        require_roles(
            UserRole.CLINICIAN, UserRole.QUALITY_LEAD, UserRole.NURSE_CLERK, UserRole.ADMIN
        )
    ),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found."
        )

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


@router.get(
    "/stream",
    summary="Server-Sent Events (SSE) stream for real-time alert updates",
)
def stream_alerts(
    patient_id: Optional[str] = None,
    max_events: Optional[int] = None,
    status_filter: str = "open",
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.CLINICIAN,
            UserRole.QUALITY_LEAD,
            UserRole.NURSE_CLERK,
            UserRole.ADMIN,
            UserRole.PATIENT,
            UserRole.CAREGIVER,
        )
    ),
):
    """Server-Sent Events (SSE) stream for real-time alert delivery.

    Adheres to Master Plan §9.2 and Phase 5 deliverables.
    Enforces active patient consent check and RBAC boundaries before streaming.
    """
    user_role = current_user.role if isinstance(current_user.role, str) else current_user.role.value

    # If patient or caregiver, patient_id is mandatory and must match
    if user_role in (UserRole.PATIENT.value, UserRole.CAREGIVER.value):
        if not patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{user_role}' requires explicit patient_id parameter.",
            )
        verify_patient_consent(patient_id=patient_id, db=db, user=current_user)
    elif patient_id:
        verify_patient_consent(patient_id=patient_id, db=db, user=current_user)

    def event_generator():
        query = select(Alert).order_by(Alert.created_at.asc())
        if patient_id:
            query = query.where(Alert.patient_id == patient_id)
        if status_filter:
            query = query.where(Alert.status == status_filter)

        alerts = db.execute(query).scalars().all()

        emitted = 0
        for alert in alerts:
            if max_events is not None and emitted >= max_events:
                break
            if not patient_id:
                try:
                    verify_patient_consent(patient_id=alert.patient_id, db=db, user=current_user)
                except HTTPException:
                    continue

            data = json.dumps(
                {
                    "id": alert.id,
                    "patient_id": alert.patient_id,
                    "risk_assessment_id": alert.risk_assessment_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "status": alert.status,
                    "trigger_reason": alert.trigger_reason,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                }
            )
            yield f"event: alert\ndata: {data}\n\n"
            emitted += 1

        yield ": keep-alive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
