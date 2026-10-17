"""Batch CSV and Excel Observation Import Engine.

Implements Master Plan §6.0, §9.3 and Phase 5b Batch Import requirements:
- Strict schema, unit-dimension, and biological plausibility validation via Analyte Registry.
- Exact and timestamp-based duplicate detection.
- Ingestion of valid rows through canonical M3/K2/M5/Audit pipeline.
- Comprehensive per-row execution report with no silent partial failure.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from vigil_api.auth import require_roles
from vigil_api.consent import verify_patient_consent
from vigil_api.database import get_db
from vigil_api.api.endpoints.patients import ingest_single_observation_internal
from vigil_api.models.v2 import Observation, Patient, User, UserRole
from vigil_core.analytes import ANALYTE_REGISTRY, check_plausibility, get_analyte
from vigil_core.units import IncompatibleUnitsError, InvalidUnitError, UnitConversionError

router = APIRouter()


class BatchImportRow(BaseModel):
    patient_id: str
    analyte_code: str
    value: float
    unit: str
    specimen_collected_at: Optional[str] = None
    laboratory_id: Optional[str] = None
    lab_changed: bool = False


class BatchImportRequest(BaseModel):
    rows: Optional[List[BatchImportRow]] = None
    csv_data: Optional[str] = None


class RowReport(BaseModel):
    row_index: int
    patient_id: str
    analyte_code: str
    value: Optional[float] = None
    unit: Optional[str] = None
    status: str  # imported, duplicate, rejected
    adjudicated_action: Optional[str] = None
    observation_id: Optional[str] = None
    alert_created: bool = False
    task_created: bool = False
    errors: List[str] = Field(default_factory=list)


class BatchImportResponse(BaseModel):
    total_rows: int
    imported_count: int
    duplicate_count: int
    rejected_count: int
    row_reports: List[RowReport]


def _parse_tabular_input(body_bytes: bytes, content_type: str) -> List[Dict[str, Any]]:
    """Parses raw request body or CSV/Excel data into a list of row dicts."""
    if not body_bytes:
        return []

    # Check for Excel
    if "excel" in content_type or "spreadsheetml" in content_type or body_bytes[:4] == b"PK\x03\x04":
        df = pd.read_excel(io.BytesIO(body_bytes))
        return df.to_dict(orient="records")

    # CSV / TSV fallback
    try:
        text = body_bytes.decode("utf-8")
        # Check delimiter
        delimiter = "\t" if "\t" in text.splitlines()[0] else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        return list(reader)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to parse CSV/Excel data: {exc}",
        )


@router.post(
    "/batch-import",
    response_model=BatchImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch import observations from CSV or Excel through no-dismissal pipeline",
)
async def batch_import_observations(
    request: Request,
    payload: Optional[BatchImportRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)),
):
    """Processes batch observation rows from CSV, Excel, or JSON.

    Validates schema, units, consent, and duplicate presence per row.
    Feeds every accepted row through M3 plausibility, K2 detector, M5 narrative, and audit.
    Returns a comprehensive per-row report.
    """
    raw_rows: List[Dict[str, Any]] = []

    # 1. Extract rows based on input format
    content_type = request.headers.get("content-type", "").lower()

    if payload and payload.rows:
        raw_rows = [r.model_dump() for r in payload.rows]
    elif payload and payload.csv_data:
        raw_rows = _parse_tabular_input(payload.csv_data.encode("utf-8"), "text/csv")
    else:
        body = await request.body()
        if body:
            raw_rows = _parse_tabular_input(body, content_type)

    if not raw_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data rows found in request body. Supply JSON rows, csv_data, or raw CSV/Excel upload.",
        )

    row_reports: List[RowReport] = []
    imported_count = 0
    duplicate_count = 0
    rejected_count = 0

    for idx, raw in enumerate(raw_rows):
        # Normalize keys (strip whitespace, lower case)
        row = {str(k).strip().lower(): v for k, v in raw.items() if k is not None}

        patient_id = str(row.get("patient_id") or row.get("patient") or "").strip()
        analyte_code = str(row.get("analyte_code") or row.get("analyte") or "").strip().lower()
        val_str = row.get("value") or row.get("result")
        unit = str(row.get("unit") or "").strip()
        specimen_date_str = row.get("specimen_collected_at") or row.get("date_drawn") or row.get("date")
        lab_id = row.get("laboratory_id")
        lab_changed = bool(row.get("lab_changed", False))

        errors: List[str] = []

        # 1. Field validation
        if not patient_id:
            errors.append("Missing required 'patient_id'.")
        if not analyte_code:
            errors.append("Missing required 'analyte_code'.")
        if val_str is None or str(val_str).strip() == "":
            errors.append("Missing required 'value'.")
        if not unit:
            errors.append("Missing required 'unit'.")

        value: Optional[float] = None
        if val_str is not None:
            try:
                value = float(val_str)
            except ValueError:
                errors.append(f"Invalid non-numeric value: '{val_str}'.")

        # Parse specimen date
        specimen_date = None
        if specimen_date_str:
            try:
                specimen_date = datetime.fromisoformat(str(specimen_date_str).replace("Z", "+00:00"))
            except Exception:
                errors.append(f"Invalid ISO-8601 specimen date: '{specimen_date_str}'.")
        else:
            specimen_date = datetime.now(timezone.utc)

        if errors:
            rejected_count += 1
            row_reports.append(
                RowReport(
                    row_index=idx,
                    patient_id=patient_id,
                    analyte_code=analyte_code,
                    value=value,
                    unit=unit,
                    status="rejected",
                    errors=errors,
                )
            )
            continue

        # 2. Check patient existence and active consent
        patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
        if patient is None:
            rejected_count += 1
            row_reports.append(
                RowReport(
                    row_index=idx,
                    patient_id=patient_id,
                    analyte_code=analyte_code,
                    value=value,
                    unit=unit,
                    status="rejected",
                    errors=[f"Patient '{patient_id}' not found in database."],
                )
            )
            continue

        try:
            verify_patient_consent(patient_id=patient.id, db=db, user=current_user)
        except HTTPException as exc:
            rejected_count += 1
            row_reports.append(
                RowReport(
                    row_index=idx,
                    patient_id=patient_id,
                    analyte_code=analyte_code,
                    value=value,
                    unit=unit,
                    status="rejected",
                    errors=[f"Consent check failed: {exc.detail}"],
                )
            )
            continue

        # 3. Check Analyte Registry and Unit Compatibility
        try:
            analyte = get_analyte(analyte_code)
            plausibility = check_plausibility(analyte.code, value, unit)
        except KeyError:
            rejected_count += 1
            row_reports.append(
                RowReport(
                    row_index=idx,
                    patient_id=patient_id,
                    analyte_code=analyte_code,
                    value=value,
                    unit=unit,
                    status="rejected",
                    errors=[f"Analyte '{analyte_code}' not recognized in Analyte Registry."],
                )
            )
            continue
        except (InvalidUnitError, IncompatibleUnitsError, UnitConversionError, ValueError) as exc:
            rejected_count += 1
            row_reports.append(
                RowReport(
                    row_index=idx,
                    patient_id=patient_id,
                    analyte_code=analyte_code,
                    value=value,
                    unit=unit,
                    status="rejected",
                    errors=[str(exc)],
                )
            )
            continue

        # 4. Duplicate Detection (patient, analyte, exact timestamp)
        existing = db.execute(
            select(Observation)
            .where(
                Observation.patient_id == patient.id,
                Observation.analyte_code == analyte_code,
                Observation.specimen_collected_at == specimen_date,
            )
        ).scalar_one_or_none()

        if existing is not None:
            duplicate_count += 1
            row_reports.append(
                RowReport(
                    row_index=idx,
                    patient_id=patient_id,
                    analyte_code=analyte_code,
                    value=value,
                    unit=unit,
                    status="duplicate",
                    observation_id=existing.id,
                    errors=[f"Duplicate observation with ID '{existing.id}' already exists at this timestamp."],
                )
            )
            continue

        # 5. Ingest through canonical pipeline
        obs, risk, alert, task, m3_result = ingest_single_observation_internal(
            db=db,
            patient=patient,
            current_user=current_user,
            analyte_code=analyte_code,
            value=value,
            unit=unit,
            specimen_collected_at=specimen_date,
            laboratory_id=str(lab_id) if lab_id else None,
            lab_changed=lab_changed,
        )

        imported_count += 1
        row_reports.append(
            RowReport(
                row_index=idx,
                patient_id=patient.id,
                analyte_code=analyte_code,
                value=value,
                unit=unit,
                status="imported",
                adjudicated_action=m3_result["action"],
                observation_id=obs.id,
                alert_created=alert is not None,
                task_created=task is not None,
                errors=[],
            )
        )

    db.commit()

    return BatchImportResponse(
        total_rows=len(raw_rows),
        imported_count=imported_count,
        duplicate_count=duplicate_count,
        rejected_count=rejected_count,
        row_reports=row_reports,
    )
