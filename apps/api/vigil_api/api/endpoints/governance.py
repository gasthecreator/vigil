"""Admin-only M11/J8 controls. Shadow aggregate outputs are never mounted on clinician endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from vigil_api import model_governance
from vigil_api.audit import record_audit_event
from vigil_api.auth import require_roles
from vigil_api.database import get_db
from vigil_api.models.v2 import User, UserRole
from vigil_api.schemas.v2 import (
    GovernanceApprovalRequest,
    GovernanceRollbackRequest,
    ShadowEvaluationRequest,
)

router = APIRouter()
admin = Depends(require_roles(UserRole.ADMIN))


def _conflict(error: ValueError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("/status")
def governance_status(db: Session = Depends(get_db), current_user: User = admin):
    try:
        return model_governance.status(db)
    except ValueError as exc:
        raise _conflict(exc) from exc


@router.post("/candidate-evaluations", status_code=status.HTTP_201_CREATED)
def start_shadow_evaluation(
    payload: ShadowEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = admin,
):
    try:
        result = model_governance.evaluate_shadow(
            db,
            current_user.id,
            payload.monitor_report,
            payload.candidate_id,
            payload.max_alert_rate_increase,
            [series.model_dump(mode="json") for series in payload.series],
        )
        record_audit_event(
            db, current_user.id, current_user.role, "model.shadow_evaluated", "model", result["evaluation_id"],
            {"candidate_id": result["candidate_id"], "monitor_report_sha256": result["monitor_report_sha256"]},
        )
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise _conflict(exc) from exc


@router.post("/approvals", status_code=status.HTTP_201_CREATED)
def approve_evaluation(
    payload: GovernanceApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = admin,
):
    try:
        result = model_governance.approve(db, current_user.id, payload.evaluation_id)
        record_audit_event(db, current_user.id, current_user.role, "model.approved", "model", payload.evaluation_id, result)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise _conflict(exc) from exc


@router.post("/promote")
def promote_evaluation(
    payload: GovernanceApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = admin,
):
    try:
        result = model_governance.promote(db, current_user.id, payload.evaluation_id)
        record_audit_event(db, current_user.id, current_user.role, "model.promoted", "model", payload.evaluation_id, result)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise _conflict(exc) from exc


@router.post("/rollback")
def rollback_model(
    payload: GovernanceRollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = admin,
):
    try:
        result = model_governance.rollback(db, current_user.id, payload.reason)
        record_audit_event(db, current_user.id, current_user.role, "model.rolled_back", "model", result["change_record_id"], result)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise _conflict(exc) from exc
