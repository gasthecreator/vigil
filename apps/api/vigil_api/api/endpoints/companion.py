"""API Endpoints for Family & Patient Companion (M8) Caregiver Sharing and Summary."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from vigil_api.api.endpoints.patients import DISCLOSURE_LOCKED_DETAIL
from vigil_api.audit import record_audit_event
from vigil_api.consent import has_active_consent
from vigil_api.database import get_db
from vigil_api.models.v2 import (
    CaregiverShare,
    FollowUpTask,
    FollowUpTaskStatus,
    Observation,
    Patient,
    RiskAssessment,
    Symptom,
    User,
    UserRole,
)
from vigil_api.schemas.v2 import (
    DisclosureReleaseRequest,
    DisclosureReleaseRequestResponse,
    PlainLanguageExplainerResponse,
    SymptomCreateRequest,
    SymptomResponse,
)
from vigil_ml.m5 import render_plain_language_explainer

router = APIRouter()


@router.get(
    "/share/{share_token}",
    status_code=status.HTTP_200_OK,
    summary="Access patient summary via scoped caregiver share token",
)
def get_caregiver_shared_summary(
    share_token: str,
    db: Session = Depends(get_db),
):
    """Retrieves patient summary accessible to an authorized family caregiver.

    Security & Attack Mitigations:
    - Rejects invalid / non-existent tokens with HTTP 404.
    - Rejects revoked tokens with HTTP 403 Forbidden.
    - Rejects expired tokens with HTTP 403 Forbidden.
    - Rejects access if patient has withdrawn active clinical consent with HTTP 403 Forbidden.
    - Strictly limits disclosed fields according to granted scope ('view_summary' vs 'full_history').
    - Hash-chained audit event recorded for every caregiver access.
    """
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(share_token.encode("utf-8")).hexdigest()

    share = db.execute(
        select(CaregiverShare).where(CaregiverShare.token_hash == token_hash)
    ).scalar_one_or_none()

    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caregiver share token not found or invalid.",
        )

    # 1. Check if token was revoked
    if share.status == "revoked" or share.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: caregiver share token has been revoked by patient.",
        )

    # 2. Check token expiration
    exp = (
        share.expires_at
        if share.expires_at.tzinfo
        else share.expires_at.replace(tzinfo=timezone.utc)
    )
    if exp <= now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: caregiver share token has expired.",
        )

    # 3. Check underlying patient consent
    dummy_user = User(
        id=f"caregiver-{share.id[:8]}",
        username=share.caregiver_name,
        role=UserRole.CAREGIVER.value,
        email="caregiver@delegated.local",
    )
    if not has_active_consent(share.patient_id, db, dummy_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: patient does not have active clinical surveillance consent.",
        )

    patient = db.execute(select(Patient).where(Patient.id == share.patient_id)).scalar_one_or_none()
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient record not found."
        )

    # 4. Fetch observations and latest risk
    obs_query = (
        select(Observation)
        .where(Observation.patient_id == share.patient_id)
        .order_by(desc(Observation.specimen_collected_at))
    )
    if share.scope == "view_summary":
        # Summary scope: only latest 3 observations
        obs_query = obs_query.limit(3)

    observations = db.execute(obs_query).scalars().all()

    latest_risk = (
        db.execute(
            select(RiskAssessment)
            .where(RiskAssessment.patient_id == share.patient_id)
            .order_by(desc(RiskAssessment.assessment_date))
        )
        .scalars()
        .first()
    )

    # 5. Record audit event
    record_audit_event(
        db=db,
        actor_id=f"caregiver:{share.caregiver_name}",
        actor_role=UserRole.CAREGIVER.value,
        action="caregiver.share_accessed",
        resource_type="PatientSummary",
        resource_id=patient.id,
        details={
            "share_id": share.id,
            "caregiver_name": share.caregiver_name,
            "scope": share.scope,
            "observations_count": len(observations),
        },
        timestamp=now,
    )
    db.commit()

    # Bad-news mode: while a clinician has not released the disclosure, an escalate-level assessment is
    # withheld from caregivers (interpretation only; raw lab values remain visible as in any lab portal).
    withheld = (
        patient.disclosure_unlocked_at is None
        and latest_risk is not None
        and (latest_risk.adjudicated_action == "escalate" or latest_risk.risk_tier == "high")
    )
    if withheld:
        latest_risk_payload = {"withheld": True, "message": DISCLOSURE_LOCKED_DETAIL["message"]}
    elif latest_risk:
        latest_risk_payload = {
            "score": latest_risk.score,
            "risk_tier": latest_risk.risk_tier,
            "adjudicated_action": latest_risk.adjudicated_action,
            "assessment_date": latest_risk.assessment_date,
        }
    else:
        latest_risk_payload = None

    return {
        "share_id": share.id,
        "patient_id": patient.id,
        "caregiver_name": share.caregiver_name,
        "relationship_type": share.relationship_type,
        "scope": share.scope,
        "status": share.status,
        "expires_at": share.expires_at,
        "patient": {
            "id": patient.id,
            "age": patient.age,
            "status": patient.status,
            "primary_cancer_type": patient.primary_cancer_type,
        },
        "observations": [
            {
                "id": o.id,
                "analyte_code": o.analyte_code,
                "value": o.value,
                "unit": o.unit,
                "specimen_collected_at": o.specimen_collected_at,
                "plausibility_status": None if withheld else o.plausibility_status,
            }
            for o in observations
        ],
        "latest_risk": latest_risk_payload,
        "synthetic": True,
    }


@router.post(
    "/share/{share_token}/symptoms",
    response_model=SymptomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record patient symptom on behalf of patient via caregiver share token",
)
def record_caregiver_symptom(
    share_token: str,
    payload: SymptomCreateRequest,
    db: Session = Depends(get_db),
):
    """Allows an authorized caregiver to record a symptom in the patient's diary."""
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(share_token.encode("utf-8")).hexdigest()

    share = db.execute(
        select(CaregiverShare).where(CaregiverShare.token_hash == token_hash)
    ).scalar_one_or_none()

    if share is None or share.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: share token is invalid or inactive.",
        )

    exp = (
        share.expires_at
        if share.expires_at.tzinfo
        else share.expires_at.replace(tzinfo=timezone.utc)
    )
    if exp <= now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: share token has expired."
        )

    dummy_user = User(
        id=f"caregiver-{share.id[:8]}",
        username=share.caregiver_name,
        role=UserRole.CAREGIVER.value,
        email="caregiver@delegated.local",
    )
    if not has_active_consent(share.patient_id, db, dummy_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: patient lacks active consent.",
        )

    symptom = Symptom(
        patient_id=share.patient_id,
        symptom_name=payload.symptom_name,
        severity=payload.severity,
        notes=payload.notes,
        input_modality=payload.input_modality,
        recorded_at=payload.recorded_at or now,
        created_at=now,
    )
    db.add(symptom)
    db.flush()

    record_audit_event(
        db=db,
        actor_id=f"caregiver:{share.caregiver_name}",
        actor_role=UserRole.CAREGIVER.value,
        action="symptom.create",
        resource_type="Symptom",
        resource_id=symptom.id,
        details={
            "patient_id": share.patient_id,
            "symptom_name": payload.symptom_name,
            "severity": payload.severity,
            "modality": payload.input_modality,
        },
        timestamp=now,
    )
    db.commit()
    db.refresh(symptom)

    return SymptomResponse(
        id=symptom.id,
        patient_id=symptom.patient_id,
        symptom_name=symptom.symptom_name,
        severity=symptom.severity,
        notes=symptom.notes,
        input_modality=symptom.input_modality,
        recorded_at=symptom.recorded_at,
        created_at=symptom.created_at,
        synthetic=True,
    )


@router.get(
    "/share/{share_token}/observations/{obs_id}/explainer",
    response_model=PlainLanguageExplainerResponse,
    status_code=status.HTTP_200_OK,
    summary="Access plain-language observation explainer via caregiver share token",
)
def get_caregiver_observation_explainer(
    share_token: str,
    obs_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves verified plain-language result explainer accessible to an authorized caregiver."""
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(share_token.encode("utf-8")).hexdigest()

    share = db.execute(
        select(CaregiverShare).where(CaregiverShare.token_hash == token_hash)
    ).scalar_one_or_none()

    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caregiver share token not found or invalid.",
        )

    if share.status == "revoked" or share.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: caregiver share token has been revoked by patient.",
        )

    exp = (
        share.expires_at
        if share.expires_at.tzinfo
        else share.expires_at.replace(tzinfo=timezone.utc)
    )
    if exp <= now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: caregiver share token has expired.",
        )

    dummy_user = User(
        id=f"caregiver-{share.id[:8]}",
        username=share.caregiver_name,
        role=UserRole.CAREGIVER.value,
        email="caregiver@delegated.local",
    )
    if not has_active_consent(share.patient_id, db, dummy_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: patient lacks active clinical surveillance consent.",
        )

    obs = db.execute(
        select(Observation).where(
            Observation.id == obs_id, Observation.patient_id == share.patient_id
        )
    ).scalar_one_or_none()

    if obs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation '{obs_id}' not found for patient.",
        )

    verdict = "explained"
    if obs.plausibility_status in {"implausible", "extreme_spike"}:
        verdict = "needs_repeat"
    else:
        risk = (
            db.execute(
                select(RiskAssessment)
                .where(RiskAssessment.patient_id == share.patient_id)
                .order_by(desc(RiskAssessment.assessment_date))
            )
            .scalars()
            .first()
        )
        if risk and risk.adjudicated_action in {"escalate", "needs_repeat", "explained"}:
            verdict = risk.adjudicated_action
        elif risk and risk.risk_tier == "high":
            verdict = "escalate"

    patient_row = db.execute(select(Patient).where(Patient.id == share.patient_id)).scalar_one()
    if verdict == "escalate" and patient_row.disclosure_unlocked_at is None:
        record_audit_event(
            db=db,
            actor_id=f"caregiver:{share.caregiver_name}",
            actor_role=UserRole.CAREGIVER.value,
            action="caregiver.observation_explainer_withheld",
            resource_type="Observation",
            resource_id=obs.id,
            details={
                "patient_id": share.patient_id,
                "share_id": share.id,
                "reason": "disclosure_locked",
            },
            timestamp=now,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=DISCLOSURE_LOCKED_DETAIL)

    explainer = render_plain_language_explainer(verdict=verdict, analyte_code=obs.analyte_code)

    record_audit_event(
        db=db,
        actor_id=f"caregiver:{share.caregiver_name}",
        actor_role=UserRole.CAREGIVER.value,
        action="caregiver.observation_explainer_read",
        resource_type="Observation",
        resource_id=obs.id,
        details={
            "patient_id": share.patient_id,
            "share_id": share.id,
            "verdict": explainer["verdict"],
        },
        timestamp=now,
    )
    db.commit()

    return PlainLanguageExplainerResponse(
        observation_id=obs.id,
        patient_id=share.patient_id,
        analyte_code=obs.analyte_code,
        verdict=explainer["verdict"],
        verbal_band=explainer["verbal_band"],
        headline=explainer["headline"],
        what_this_means=explainer["what_this_means"],
        recommended_action=explainer["recommended_action"],
        questions_to_ask_your_doctor=explainer["questions_to_ask_your_doctor"],
        flesch_kincaid_grade_level=explainer["flesch_kincaid_grade_level"],
        word_count=explainer["word_count"],
        verified=explainer["verified"],
        synthetic=True,
    )


@router.post(
    "/share/{share_token}/disclosure/request-release",
    response_model=DisclosureReleaseRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Caregiver requests clinician release of sensitive diagnostic results on behalf of patient",
)
def caregiver_request_disclosure_release(
    share_token: str,
    payload: DisclosureReleaseRequest,
    db: Session = Depends(get_db),
):
    """Allows an authorized caregiver to submit a clinician release request for sensitive findings."""
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(share_token.encode("utf-8")).hexdigest()

    share = db.execute(
        select(CaregiverShare).where(CaregiverShare.token_hash == token_hash)
    ).scalar_one_or_none()

    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caregiver share token not found or invalid.",
        )

    if share.status == "revoked" or share.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: caregiver share token has been revoked by patient.",
        )

    exp = (
        share.expires_at
        if share.expires_at.tzinfo
        else share.expires_at.replace(tzinfo=timezone.utc)
    )
    if exp <= now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: caregiver share token has expired.",
        )

    dummy_user = User(
        id=f"caregiver-{share.id[:8]}",
        username=share.caregiver_name,
        role=UserRole.CAREGIVER.value,
        email="caregiver@delegated.local",
    )
    if not has_active_consent(share.patient_id, db, dummy_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: patient lacks active clinical surveillance consent.",
        )

    task_id = str(uuid.uuid4())
    notes_text = (
        f"Caregiver '{share.caregiver_name}' requested clinician release of sensitive/escalate results. "
        f"Caregiver Note: {payload.reason or 'Caregiver requested release.'}"
    )

    task = FollowUpTask(
        id=task_id,
        patient_id=share.patient_id,
        alert_id=None,
        task_type="disclosure_release_request",
        status=FollowUpTaskStatus.PENDING.value,
        due_date=now + timedelta(days=1),
        escalation_level=1,
        notes=notes_text,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.flush()

    record_audit_event(
        db=db,
        actor_id=f"caregiver:{share.caregiver_name}",
        actor_role=UserRole.CAREGIVER.value,
        action="caregiver.disclosure_release_requested",
        resource_type="FollowUpTask",
        resource_id=task.id,
        details={
            "patient_id": share.patient_id,
            "share_id": share.id,
            "reason": payload.reason,
        },
        timestamp=now,
    )
    db.commit()

    return DisclosureReleaseRequestResponse(
        requested=True,
        task_id=task.id,
        message="Request submitted. A clinician will review and release results.",
        synthetic=True,
    )
