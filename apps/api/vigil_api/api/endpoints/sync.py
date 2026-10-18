"""Offline Synchronization Service for Vigil Precision Oncology Platform.

Adheres to MASTER_PLAN.md §9.2, WP5.5, and Phase 5 deliverables:
- Handles batch queue replay from offline clinician workstations & PWAs.
- Strict idempotency keys prevent duplicate ingestion on network retries.
- Last-Write-Wins (LWW) conflict resolution with server-state reporting.
- All observation mutations strictly routed through the unit-safe no-dismissal pipeline.
- Audit logging for every processed sync batch.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_api.api.endpoints.patients import ingest_single_observation_internal
from vigil_api.audit import record_audit_event
from vigil_api.auth import require_roles
from vigil_api.consent import verify_patient_consent
from vigil_api.database import get_db
from vigil_api.models.v2 import (
    Alert,
    AlertAcknowledgement,
    AlertStatus,
    FollowUpTask,
    IdempotencyRecord,
    User,
    UserRole,
)

router = APIRouter()


class SyncMutationItem(BaseModel):
    client_mutation_id: str = Field(..., description="Unique client-generated idempotency key")
    entity_type: str = Field(
        ..., description="'observation', 'follow_up_task', or 'alert_acknowledgement'"
    )
    action: str = Field("create", description="'create' or 'update'")
    entity_id: Optional[str] = Field(None, description="Target entity ID if updating")
    patient_id: str = Field(..., description="Target patient UUID")
    client_updated_at: datetime = Field(..., description="Client timestamp when mutation occurred")
    payload: Dict[str, Any] = Field(..., description="Mutation payload")


class SyncBatchRequest(BaseModel):
    sync_id: str = Field(..., description="Unique client batch transaction identifier")
    client_device_id: Optional[str] = Field(
        None, description="Originating device or workstation ID"
    )
    client_timestamp: datetime = Field(..., description="Timestamp when batch was dispatched")
    mutations: List[SyncMutationItem] = Field(..., description="Array of queued mutations")


class SyncMutationResult(BaseModel):
    client_mutation_id: str
    status: str  # "applied", "already_applied", "conflict_server_wins", "rejected"
    entity_id: Optional[str] = None
    server_updated_at: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SyncBatchResponse(BaseModel):
    sync_id: str
    total_mutations: int
    applied_count: int
    already_applied_count: int
    conflict_count: int
    rejected_count: int
    results: List[SyncMutationResult]
    processed_at: str


@router.post(
    "/batch",
    response_model=SyncBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Process offline sync batch replay with idempotency and LWW conflict resolution",
)
def process_sync_batch(
    payload: SyncBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CLINICIAN, UserRole.NURSE_CLERK, UserRole.ADMIN)
    ),
):
    """Replays queued client mutations accumulated during offline clinic operations."""
    now = datetime.now(timezone.utc)
    results: List[SyncMutationResult] = []

    applied_count = 0
    already_applied_count = 0
    conflict_count = 0
    rejected_count = 0

    for item in payload.mutations:
        # 1. Consent & Patient Verification FIRST (P8-B)
        try:
            patient = verify_patient_consent(patient_id=item.patient_id, db=db, user=current_user)
        except HTTPException as e:
            rejected_count += 1
            results.append(
                SyncMutationResult(
                    client_mutation_id=item.client_mutation_id,
                    status="rejected",
                    error=f"Consent/Auth check failed: {e.detail}",
                )
            )
            continue

        # 2. Idempotency Check scoped to (patient_id, client_mutation_id) (P8-B)
        existing_idemp = db.execute(
            select(IdempotencyRecord).where(
                IdempotencyRecord.patient_id == item.patient_id,
                IdempotencyRecord.idempotency_key == item.client_mutation_id,
            )
        ).scalar_one_or_none()

        if existing_idemp is not None:
            already_applied_count += 1
            results.append(
                SyncMutationResult(
                    client_mutation_id=item.client_mutation_id,
                    status="already_applied",
                    entity_id=existing_idemp.entity_id,
                    details=existing_idemp.response_payload,
                )
            )
            continue

        client_time = (
            item.client_updated_at
            if item.client_updated_at.tzinfo
            else item.client_updated_at.replace(tzinfo=timezone.utc)
        )

        try:
            # 3. Process by Entity Type
            if item.entity_type == "observation":
                spec_time = item.payload.get("specimen_collected_at")
                if isinstance(spec_time, str):
                    try:
                        spec_time = datetime.fromisoformat(spec_time.replace("Z", "+00:00"))
                    except Exception:
                        spec_time = now
                elif spec_time is None:
                    spec_time = client_time

                obs, risk, alert, task, m3_result = ingest_single_observation_internal(
                    db=db,
                    patient=patient,
                    current_user=current_user,
                    analyte_code=item.payload.get("analyte_code"),
                    value=float(item.payload.get("value")),
                    unit=item.payload.get("unit"),
                    specimen_collected_at=spec_time,
                    laboratory_id=item.payload.get("laboratory_id"),
                    lab_changed=item.payload.get("lab_changed", False),
                )

                resp_payload = {
                    "observation_id": obs.id,
                    "risk_assessment_id": risk.id if risk is not None else None,
                    "action": m3_result["action"],
                }

                # Record idempotency
                idemp = IdempotencyRecord(
                    patient_id=patient.id,
                    idempotency_key=item.client_mutation_id,
                    entity_type="observation",
                    entity_id=obs.id,
                    status="applied",
                    response_payload=resp_payload,
                    created_at=now,
                )
                db.add(idemp)
                db.flush()

                applied_count += 1
                results.append(
                    SyncMutationResult(
                        client_mutation_id=item.client_mutation_id,
                        status="applied",
                        entity_id=obs.id,
                        details=resp_payload,
                    )
                )

            elif item.entity_type == "follow_up_task":
                task_id = item.entity_id or item.payload.get("task_id")
                task = db.execute(
                    select(FollowUpTask).where(FollowUpTask.id == task_id)
                ).scalar_one_or_none()
                if task is None:
                    rejected_count += 1
                    results.append(
                        SyncMutationResult(
                            client_mutation_id=item.client_mutation_id,
                            status="rejected",
                            error=f"Task '{task_id}' not found",
                        )
                    )
                    continue

                server_time = (
                    task.updated_at
                    if task.updated_at.tzinfo
                    else task.updated_at.replace(tzinfo=timezone.utc)
                )

                # Last-Write-Wins (LWW) check
                if client_time <= server_time:
                    conflict_count += 1
                    results.append(
                        SyncMutationResult(
                            client_mutation_id=item.client_mutation_id,
                            status="conflict_server_wins",
                            entity_id=task.id,
                            server_updated_at=server_time.isoformat(),
                            details={"server_status": task.status, "notes": task.notes},
                        )
                    )
                    continue

                # Apply client update
                if "status" in item.payload:
                    task.status = item.payload["status"]
                if "notes" in item.payload:
                    task.notes = item.payload["notes"]
                task.updated_at = now
                db.flush()

                idemp = IdempotencyRecord(
                    patient_id=patient.id,
                    idempotency_key=item.client_mutation_id,
                    entity_type="follow_up_task",
                    entity_id=task.id,
                    status="applied",
                    response_payload={"task_id": task.id, "status": task.status},
                    created_at=now,
                )
                db.add(idemp)
                db.flush()

                applied_count += 1
                results.append(
                    SyncMutationResult(
                        client_mutation_id=item.client_mutation_id,
                        status="applied",
                        entity_id=task.id,
                        server_updated_at=now.isoformat(),
                    )
                )

            elif item.entity_type == "alert_acknowledgement":
                alert_id = item.entity_id or item.payload.get("alert_id")
                alert = db.execute(select(Alert).where(Alert.id == alert_id)).scalar_one_or_none()
                if alert is None:
                    rejected_count += 1
                    results.append(
                        SyncMutationResult(
                            client_mutation_id=item.client_mutation_id,
                            status="rejected",
                            error=f"Alert '{alert_id}' not found",
                        )
                    )
                    continue

                if alert.status == AlertStatus.ACKNOWLEDGED.value:
                    conflict_count += 1
                    results.append(
                        SyncMutationResult(
                            client_mutation_id=item.client_mutation_id,
                            status="conflict_server_wins",
                            entity_id=alert.id,
                            details={"server_status": alert.status},
                        )
                    )
                    continue

                ack = AlertAcknowledgement(
                    alert_id=alert.id,
                    user_id=current_user.id,
                    disposition=item.payload.get("disposition", "clinical_hold"),
                    rationale_text=item.payload.get("rationale_text", "Offline sync disposition"),
                    acknowledged_at=client_time,
                )
                db.add(ack)
                alert.status = AlertStatus.ACKNOWLEDGED.value
                db.flush()

                idemp = IdempotencyRecord(
                    patient_id=patient.id,
                    idempotency_key=item.client_mutation_id,
                    entity_type="alert_acknowledgement",
                    entity_id=alert.id,
                    status="applied",
                    response_payload={"alert_id": alert.id, "disposition": ack.disposition},
                    created_at=now,
                )
                db.add(idemp)
                db.flush()

                applied_count += 1
                results.append(
                    SyncMutationResult(
                        client_mutation_id=item.client_mutation_id,
                        status="applied",
                        entity_id=alert.id,
                    )
                )

            else:
                rejected_count += 1
                results.append(
                    SyncMutationResult(
                        client_mutation_id=item.client_mutation_id,
                        status="rejected",
                        error=f"Unsupported entity_type: '{item.entity_type}'",
                    )
                )

        except Exception as e:
            rejected_count += 1
            results.append(
                SyncMutationResult(
                    client_mutation_id=item.client_mutation_id,
                    status="rejected",
                    error=f"Processing exception: {str(e)}",
                )
            )

    # Record Audit Event
    record_audit_event(
        db=db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="sync.batch_processed",
        resource_type="SyncBatch",
        resource_id=payload.sync_id,
        details={
            "total_mutations": len(payload.mutations),
            "applied_count": applied_count,
            "already_applied_count": already_applied_count,
            "conflict_count": conflict_count,
            "rejected_count": rejected_count,
            "client_device_id": payload.client_device_id,
        },
        timestamp=now,
    )

    db.commit()

    return SyncBatchResponse(
        sync_id=payload.sync_id,
        total_mutations=len(payload.mutations),
        applied_count=applied_count,
        already_applied_count=already_applied_count,
        conflict_count=conflict_count,
        rejected_count=rejected_count,
        results=results,
        processed_at=now.isoformat(),
    )
