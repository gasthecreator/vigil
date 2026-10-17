"""HL7 v2 ORU^R01 Observation Ingestion Endpoint.

Implements Master Plan §9.6 and Phase 5 Platform requirements:
- Receives HL7 v2 ORU^R01 unsolicited observation result messages.
- Parses MSH, PID, OBR, OBX segments using vigil_core.hl7.
- Enforces patient consent and RBAC (Clinician, Nurse Clerk, Admin).
- Ingests each OBX observation through the canonical M3/K2/M5/Audit pipeline.
- Returns detailed per-observation ingestion report.
"""

from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_api.api.endpoints.patients import ingest_single_observation_internal
from vigil_api.audit import record_audit_event
from vigil_api.auth import require_roles
from vigil_api.consent import verify_patient_consent
from vigil_api.database import get_db
from vigil_api.models.v2 import Patient, User, UserRole
from vigil_core.hl7 import HL7ParsingError, parse_oru_r01

router = APIRouter()


class HL7ObservationImportReport(BaseModel):
    set_id: int
    analyte_code: str
    loinc_code: Optional[str] = None
    value: float
    unit: str
    status: str  # imported, rejected
    adjudicated_action: Optional[str] = None
    observation_id: Optional[str] = None
    alert_created: bool = False
    task_created: bool = False
    errors: List[str] = Field(default_factory=list)


class HL7ORUImportResponse(BaseModel):
    message_control_id: str
    patient_id: str
    total_observations: int
    imported_count: int
    rejected_count: int
    observation_reports: List[HL7ObservationImportReport]


class HL7MessageRequest(BaseModel):
    hl7_message: str


@router.post(
    "/oru-r01",
    response_model=HL7ORUImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest HL7 v2 ORU^R01 unsolicited laboratory result message",
)
async def ingest_hl7_oru_r01(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)
    ),
):
    """Processes an HL7 v2 ORU^R01 message containing laboratory observations."""
    content_type = request.headers.get("content-type", "").lower()
    body_bytes = await request.body()
    if not body_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty request body. Send raw HL7 v2 text or JSON with 'hl7_message'.",
        )

    raw_message = ""
    if "application/json" in content_type or body_bytes.strip().startswith(b"{"):
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
            raw_message = payload.get("hl7_message", "")
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid JSON body: {exc}",
            )
    else:
        try:
            raw_message = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_message = body_bytes.decode("latin-1")

    if not raw_message or not raw_message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing HL7 message text.",
        )

    # 1. Parse HL7 message
    try:
        parsed_msg = parse_oru_r01(raw_message)
    except HL7ParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"HL7 ORU^R01 parsing failed: {str(exc)}",
        )

    # 2. Lookup Patient & Verify Consent
    patient = (
        db.execute(select(Patient).where(Patient.id == parsed_msg.patient_id)).scalars().first()
    )
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{parsed_msg.patient_id}' not found for HL7 message '{parsed_msg.message_control_id}'.",
        )

    verify_patient_consent(patient_id=patient.id, db=db, user=current_user)

    # 3. Ingest each observation
    reports: List[HL7ObservationImportReport] = []
    imported_count = 0
    rejected_count = 0

    for obs in parsed_msg.observations:
        try:
            obs_record, risk_record, alert, task, m3_res = ingest_single_observation_internal(
                db=db,
                patient=patient,
                current_user=current_user,
                analyte_code=obs.analyte_code,
                value=obs.value,
                unit=obs.unit,
                specimen_collected_at=obs.specimen_collected_at,
                laboratory_id=obs.laboratory_id,
            )
            imported_count += 1
            reports.append(
                HL7ObservationImportReport(
                    set_id=obs.set_id,
                    analyte_code=obs.analyte_code,
                    loinc_code=obs.loinc_code,
                    value=obs.value,
                    unit=obs.unit,
                    status="imported",
                    adjudicated_action=m3_res["action"],
                    observation_id=obs_record.id,
                    alert_created=alert is not None,
                    task_created=task is not None,
                    errors=[],
                )
            )
        except HTTPException as exc:
            rejected_count += 1
            reports.append(
                HL7ObservationImportReport(
                    set_id=obs.set_id,
                    analyte_code=obs.analyte_code,
                    loinc_code=obs.loinc_code,
                    value=obs.value,
                    unit=obs.unit,
                    status="rejected",
                    errors=[str(exc.detail)],
                )
            )

    # 4. Record Audit Event
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role
        if isinstance(current_user.role, str)
        else current_user.role.value,
        action="hl7_oru_r01_imported",
        resource_type="patient",
        resource_id=patient.id,
        details={
            "message_control_id": parsed_msg.message_control_id,
            "sending_facility": parsed_msg.sending_facility,
            "total_observations": len(parsed_msg.observations),
            "imported_count": imported_count,
            "rejected_count": rejected_count,
        },
    )

    db.commit()

    return HL7ORUImportResponse(
        message_control_id=parsed_msg.message_control_id,
        patient_id=patient.id,
        total_observations=len(parsed_msg.observations),
        imported_count=imported_count,
        rejected_count=rejected_count,
        observation_reports=reports,
    )
