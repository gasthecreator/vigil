"""HL7 FHIR R4 Observation Export and Import Endpoints.

Implements Master Plan §6.0, §9.3 and Phase 5b FHIR requirements:
- GET /api/v1/fhir/Observation/{id}: Exports clinical observation in standard HL7 FHIR R4 with LOINC and UCUM.
- POST /api/v1/fhir/Observation: Ingests FHIR R4 Observation through canonical M3/K2/M5/Audit pipeline.
- Audited reads and writes with patient consent verification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from vigil_api.audit import record_audit_event
from vigil_api.auth import get_current_user, require_roles
from vigil_api.consent import verify_patient_consent
from vigil_api.database import get_db
from vigil_api.api.endpoints.patients import ingest_single_observation_internal
from vigil_api.models.v2 import Observation, Patient, User, UserRole
from vigil_core.fhir import fhir_to_observation, observation_to_fhir

router = APIRouter()


@router.get(
    "/Observation/{id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Export observation as HL7 FHIR R4 Observation resource",
)
def export_fhir_observation(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves an observation and formats it as an HL7 FHIR R4 Observation resource."""
    obs = db.execute(select(Observation).where(Observation.id == id)).scalar_one_or_none()
    if obs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation '{id}' not found.",
        )

    # Enforce patient consent and RBAC
    verify_patient_consent(patient_id=obs.patient_id, db=db, user=current_user)

    # Record read audit event
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="fhir.observation.read",
        resource_type="Observation",
        resource_id=obs.id,
        details={"patient_id": obs.patient_id, "analyte_code": obs.analyte_code},
    )
    db.commit()

    effective_str = (
        obs.specimen_collected_at.isoformat()
        if obs.specimen_collected_at
        else datetime.now(timezone.utc).isoformat()
    )

    fhir_resource = observation_to_fhir(
        analyte_code=obs.analyte_code,
        value=float(obs.value),
        unit=obs.unit,
        patient_id=obs.patient_id,
        observation_id=obs.id,
        effective_datetime=effective_str,
        status="final" if obs.status == "accepted" else "preliminary",
        is_synthetic=True,
    )
    return fhir_resource


@router.post(
    "/Observation",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Import HL7 FHIR R4 Observation resource through surveillance pipeline",
)
def import_fhir_observation(
    resource: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)),
):
    """Ingests an HL7 FHIR R4 Observation resource into Vigil.

    Resolves LOINC code to internal analyte, verifies consent, executes M3 plausibility,
    updates K2 detector, evaluates M5 clinical narrative, and logs audit event.
    """
    try:
        parsed = fhir_to_observation(resource)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    patient_id = parsed.get("patient_id")
    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="FHIR Observation must reference a valid Patient in subject.reference.",
        )

    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referenced patient '{patient_id}' not found.",
        )

    # Verify patient consent
    verify_patient_consent(patient_id=patient.id, db=db, user=current_user)

    analyte_code = parsed.get("analyte_code")
    if not analyte_code:
        loinc = parsed.get("loinc_code")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unrecognized or unmapped LOINC code '{loinc}'. Must map to supported analyte.",
        )

    value = parsed.get("value")
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Observation resource must specify a valueQuantity with numeric value.",
        )

    unit = parsed.get("unit")
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Observation resource must specify a valueQuantity unit or code.",
        )

    effective_dt = None
    if parsed.get("effective_datetime"):
        try:
            effective_dt = datetime.fromisoformat(parsed["effective_datetime"].replace("Z", "+00:00"))
        except Exception:
            pass

    # Feed through canonical no-dismissal pipeline
    obs, risk, alert, task, m3_result = ingest_single_observation_internal(
        db=db,
        patient=patient,
        current_user=current_user,
        analyte_code=analyte_code,
        value=float(value),
        unit=unit,
        specimen_collected_at=effective_dt,
    )
    db.commit()

    effective_str = (
        obs.specimen_collected_at.isoformat()
        if obs.specimen_collected_at
        else datetime.now(timezone.utc).isoformat()
    )

    return observation_to_fhir(
        analyte_code=obs.analyte_code,
        value=float(obs.value),
        unit=obs.unit,
        patient_id=obs.patient_id,
        observation_id=obs.id,
        effective_datetime=effective_str,
        status="final",
        is_synthetic=True,
    )
