"""Pydantic v2 schemas for Vigil Precision Oncology Platform."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ObservationCreateRequest(BaseModel):
    analyte_code: str = Field(..., description="Analyte code from vigil_core.analytes (e.g. 'ca_15_3', 'cea')")
    value: float = Field(..., description="Observed raw numeric value")
    unit: str = Field(..., description="Input unit string (e.g. 'U/mL', 'kU/L', '[iU]/mL')")
    specimen_collected_at: Optional[datetime] = Field(None, description="Timestamp when specimen was drawn")
    laboratory_id: Optional[str] = Field(None, description="Identifier of executing laboratory")
    lab_changed: bool = Field(False, description="Flag indicating if analyzer/lab changed from previous draw")


class RiskAssessmentSummary(BaseModel):
    id: str
    assessment_date: datetime
    model_versions: Dict[str, str]
    input_hash: str
    score: float
    risk_tier: str
    uncertainty: Optional[Dict[str, Any]] = None
    adjudicated_action: str
    clinical_note: Optional[str] = None
    abstention: bool = False


class AlertSummary(BaseModel):
    id: str
    alert_type: str
    severity: str
    trigger_reason: str
    status: str
    created_at: datetime


class FollowUpTaskSummary(BaseModel):
    id: str
    task_type: str
    status: str
    due_date: datetime
    escalation_level: int
    notes: Optional[str] = None


class ObservationCreateResponse(BaseModel):
    observation_id: str
    patient_id: str
    analyte_code: str
    canonical_value: float
    canonical_unit: str
    raw_value: float
    raw_unit: str
    specimen_collected_at: datetime
    plausibility_status: str
    adjudicated_action: str
    risk_assessment: RiskAssessmentSummary
    alert: Optional[AlertSummary] = None
    follow_up_task: Optional[FollowUpTaskSummary] = None
    synthetic: bool = True  # Invariant: Responses carry the synthetic flag


class AlertAcknowledgeRequest(BaseModel):
    disposition: str = Field(..., description="Disposition code from AlertDisposition")
    rationale_text: Optional[str] = Field(None, description="Clinician justification for alert disposition")
    note: Optional[str] = Field(None, description="Clinician note or justification")


class AlertAcknowledgeResponse(BaseModel):
    alert_id: str
    status: str
    disposition: str
    rationale_text: str
    acknowledged_at: datetime
    acknowledged_by: str
    synthetic: bool = True


class ConsentCreateRequest(BaseModel):
    consent_type: str = Field("surveillance_monitoring", description="Type of clinical consent")
    granted: bool = Field(True, description="Whether consent is granted")
    scope: str = Field("full", description="Consent scope e.g. clinical_care, full")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    withdrawn_at: Optional[datetime] = Field(None, description="Withdrawal date")


class FollowUpTransitionRequest(BaseModel):
    target_status: str = Field(..., description="Target status from FollowUpTaskStatus")
    reason: Optional[str] = Field(None, description="Optional clinical note explaining state transition")


class FollowUpTaskResponse(BaseModel):
    task_id: str
    patient_id: str
    task_type: str
    status: str
    due_date: datetime
    escalation_level: int
    notes: Optional[str] = None
    synthetic: bool = True


class AuditVerifyResponse(BaseModel):
    valid: bool
    verified_events: int
    total_events: int
    head_hash: Optional[str] = None
    error: Optional[str] = None
    tampered_event_id: Optional[str] = None


class PatientV2Response(BaseModel):
    id: str
    facility_id: Optional[str] = None
    mrn: Optional[str] = None
    external_id: Optional[str] = None
    age: Optional[int] = None
    biological_sex: str
    primary_cancer_type: str
    synthetic: bool = True
    status: str
    created_at: datetime
    updated_at: datetime
