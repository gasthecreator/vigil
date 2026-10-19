"""Local OCR lab-report drafts. Suggestions never enter the record without a human confirm body."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_api.api.endpoints.patients import ingest_single_observation_internal
from vigil_api.audit import record_audit_event
from vigil_api.auth import require_roles
from vigil_api.consent import verify_patient_consent
from vigil_api.database import get_db
from vigil_api.models.v2 import OcrDraft, User, UserRole
from vigil_api.ocr import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES, extract_from_bytes
from vigil_api.schemas.v2 import (
    AlertSummary,
    FollowUpTaskSummary,
    ObservationCreateResponse,
    OcrConfusionFlag,
    OcrDraftConfirmRequest,
    OcrDraftConfirmResponse,
    OcrDraftResponse,
    OcrDraftUploadRequest,
    OcrSuggestion,
    RiskAssessmentSummary,
)

router = APIRouter()

_UPLOAD_ROLES = (
    UserRole.PATIENT,
    UserRole.CAREGIVER,
    UserRole.CLINICIAN,
    UserRole.NURSE_CLERK,
    UserRole.ADMIN,
)
_READ_ROLES = (
    UserRole.PATIENT,
    UserRole.CAREGIVER,
    UserRole.CLINICIAN,
    UserRole.NURSE_CLERK,
    UserRole.QUALITY_LEAD,
    UserRole.ADMIN,
)
_CONFIRM_ROLES = (UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)
_REJECT_ROLES = (
    UserRole.PATIENT,
    UserRole.CAREGIVER,
    UserRole.CLINICIAN,
    UserRole.NURSE_CLERK,
    UserRole.ADMIN,
)


def _to_response(draft: OcrDraft) -> OcrDraftResponse:
    suggestion = draft.suggestion or {}
    flags = [
        OcrConfusionFlag(field=f["field"], reason=f["reason"])
        for f in (draft.confusion_flags or [])
        if isinstance(f, dict) and "field" in f and "reason" in f
    ]
    return OcrDraftResponse(
        id=draft.id,
        patient_id=draft.patient_id,
        filename=draft.filename,
        content_type=draft.content_type,
        source_sha256=draft.source_sha256,
        engine=draft.engine,
        extracted_text=draft.extracted_text,
        suggestion=OcrSuggestion(
            analyte_code=suggestion.get("analyte_code"),
            analyte_name=suggestion.get("analyte_name"),
            value=suggestion.get("value"),
            unit=suggestion.get("unit"),
            specimen_collected_at=suggestion.get("specimen_collected_at"),
            flags=[
                OcrConfusionFlag(field=f["field"], reason=f["reason"])
                for f in suggestion.get("flags") or []
                if isinstance(f, dict)
            ],
        ),
        confusion_flags=flags,
        status=draft.status,
        created_by=draft.created_by,
        created_at=draft.created_at,
        resolved_at=draft.resolved_at,
        resolved_by=draft.resolved_by,
        observation_id=draft.observation_id,
        synthetic=True,
    )


def _load_draft(db: Session, patient_id: str, draft_id: str) -> OcrDraft:
    draft = db.execute(
        select(OcrDraft).where(OcrDraft.id == draft_id, OcrDraft.patient_id == patient_id)
    ).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR draft not found.")
    return draft


@router.post(
    "/{id}/ocr-drafts",
    response_model=OcrDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ocr_draft(
    id: str,
    payload: OcrDraftUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_UPLOAD_ROLES)),
):
    """Store a local extraction as a *draft*. Does not create an observation."""
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    ctype = payload.content_type.split(";")[0].strip().lower()
    if ctype not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"content_type must be one of {sorted(ALLOWED_CONTENT_TYPES)}.",
        )
    try:
        raw = base64.b64decode(payload.content_base64, validate=False)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="content_base64 is not valid base64.",
        ) from exc
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="decoded document is empty.",
        )
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"document exceeds {MAX_UPLOAD_BYTES} bytes.",
        )
    try:
        extracted = extract_from_bytes(raw, ctype)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    flags = [{"field": f.field, "reason": f.reason} for f in extracted.suggestion.flags]
    draft = OcrDraft(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        filename=payload.filename[:255],
        content_type=ctype,
        source_sha256=extracted.source_sha256,
        engine=extracted.engine,
        extracted_text=(extracted.text or "")[:20000],
        suggestion=extracted.suggestion.as_dict(),
        confusion_flags=flags,
        status="pending",
        created_by=current_user.id,
    )
    db.add(draft)
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="ocr_draft.created",
        resource_type="OcrDraft",
        resource_id=draft.id,
        details={
            "patient_id": patient.id,
            "engine": draft.engine,
            "filename": draft.filename,
            "source_sha256": draft.source_sha256,
        },
    )
    db.commit()
    db.refresh(draft)
    return _to_response(draft)


@router.get("/{id}/ocr-drafts", response_model=List[OcrDraftResponse])
def list_ocr_drafts(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_READ_ROLES)),
):
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    rows = (
        db.execute(
            select(OcrDraft)
            .where(OcrDraft.patient_id == patient.id)
            .order_by(OcrDraft.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [_to_response(r) for r in rows]


@router.get("/{id}/ocr-drafts/{draft_id}", response_model=OcrDraftResponse)
def get_ocr_draft(
    id: str,
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_READ_ROLES)),
):
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    return _to_response(_load_draft(db, patient.id, draft_id))


@router.post(
    "/{id}/ocr-drafts/{draft_id}/confirm",
    response_model=OcrDraftConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_ocr_draft(
    id: str,
    draft_id: str,
    payload: OcrDraftConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_CONFIRM_ROLES)),
):
    """Write an observation from the *human-posted* fields. OCR suggestion values are ignored."""
    if payload.confirmed is not True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="confirmed must be true; the server will not copy OCR suggestions.",
        )
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    draft = _load_draft(db, patient.id, draft_id)
    if draft.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"draft is {draft.status}; only pending drafts can be confirmed.",
        )

    obs, risk, alert, task, m3_result = ingest_single_observation_internal(
        db=db,
        patient=patient,
        current_user=current_user,
        analyte_code=payload.analyte_code,
        value=payload.value,
        unit=payload.unit,
        specimen_collected_at=payload.specimen_collected_at,
        laboratory_id=payload.laboratory_id,
        lab_changed=payload.lab_changed,
    )
    now = datetime.now(timezone.utc)
    draft.status = "confirmed"
    draft.resolved_at = now
    draft.resolved_by = current_user.id
    draft.observation_id = obs.id
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="ocr_draft.confirmed",
        resource_type="OcrDraft",
        resource_id=draft.id,
        details={
            "patient_id": patient.id,
            "observation_id": obs.id,
            "analyte_code": payload.analyte_code,
            "suggestion_ignored": True,
        },
    )
    db.commit()

    alert_summary = (
        AlertSummary(
            id=alert.id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            trigger_reason=alert.trigger_reason,
            status=alert.status,
            created_at=alert.created_at,
        )
        if alert
        else None
    )
    follow_up_summary = (
        FollowUpTaskSummary(
            id=task.id,
            task_type=task.task_type,
            status=task.status,
            due_date=task.due_date,
            escalation_level=task.escalation_level,
            notes=task.notes,
        )
        if task
        else None
    )
    created = ObservationCreateResponse(
        observation_id=obs.id,
        patient_id=patient.id,
        analyte_code=obs.analyte_code,
        canonical_value=obs.value,
        canonical_unit=obs.unit,
        raw_value=obs.raw_value,
        raw_unit=obs.raw_unit,
        specimen_collected_at=obs.specimen_collected_at,
        plausibility_status=obs.plausibility_status,
        adjudicated_action=m3_result["action"],
        risk_assessment=(
            RiskAssessmentSummary(
                id=risk.id,
                assessment_date=risk.assessment_date,
                model_versions=risk.model_versions,
                input_hash=risk.input_hash,
                score=risk.score,
                risk_tier=risk.risk_tier,
                uncertainty=risk.uncertainty,
                adjudicated_action=risk.adjudicated_action,
                clinical_note=risk.clinical_note,
                abstention=risk.abstention,
            )
            if risk is not None
            else None
        ),
        alert=alert_summary,
        follow_up_task=follow_up_summary,
        outputs_withheld=risk is None,
        synthetic=True,
    )
    return OcrDraftConfirmResponse(
        **created.model_dump(), draft_id=draft.id, draft_status="confirmed"
    )


@router.post("/{id}/ocr-drafts/{draft_id}/reject", response_model=OcrDraftResponse)
def reject_ocr_draft(
    id: str,
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_REJECT_ROLES)),
):
    patient = verify_patient_consent(patient_id=id, db=db, user=current_user)
    draft = _load_draft(db, patient.id, draft_id)
    if draft.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"draft is {draft.status}; only pending drafts can be rejected.",
        )
    draft.status = "rejected"
    draft.resolved_at = datetime.now(timezone.utc)
    draft.resolved_by = current_user.id
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="ocr_draft.rejected",
        resource_type="OcrDraft",
        resource_id=draft.id,
        details={"patient_id": patient.id},
    )
    db.commit()
    db.refresh(draft)
    return _to_response(draft)
