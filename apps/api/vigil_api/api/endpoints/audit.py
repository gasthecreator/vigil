"""API Endpoints for Hash-Chained Audit Trail Verification and Inspection."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_api.audit import verify_audit_chain
from vigil_api.auth import require_roles
from vigil_api.database import get_db
from vigil_api.models.v2 import AuditEvent, User, UserRole
from vigil_api.schemas.v2 import AuditVerifyResponse

router = APIRouter()


@router.get(
    "/verify",
    response_model=AuditVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify cryptographic integrity of the audit log chain",
)
def verify_audit_log(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.QUALITY_LEAD, UserRole.ADMIN, UserRole.CLINICIAN)
    ),
):
    """Iterates through all audit events, verifying backlink hashes and payload signatures.

    Returns 200 with valid=True if unbroken, or valid=False with tampered_event_id.
    """
    verification_result = verify_audit_chain(db)
    return verification_result


@router.get(
    "/events",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List recent audit events",
)
def list_audit_events(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.QUALITY_LEAD, UserRole.ADMIN)),
):
    """Retrieve recent cryptographically chained audit events."""
    events = (
        db.execute(
            select(AuditEvent)
            .order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc())
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": ev.id,
            "timestamp": ev.timestamp.isoformat(),
            "actor_id": ev.actor_id,
            "actor_role": ev.actor_role,
            "action": ev.action,
            "resource_type": ev.resource_type,
            "resource_id": ev.resource_id,
            "details": ev.details,
            "prev_hash": ev.prev_hash,
            "curr_hash": ev.curr_hash,
        }
        for ev in events
    ]
