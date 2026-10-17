"""Pydantic v2 schemas for Vigil Precision Oncology Platform."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ObservationCreateRequest(BaseModel):
    analyte_code: str = Field(
        ..., description="Analyte code from vigil_core.analytes (e.g. 'ca_15_3', 'cea')"
    )
    value: float = Field(..., description="Observed raw numeric value")
    unit: str = Field(..., description="Input unit string (e.g. 'U/mL', 'kU/L', '[iU]/mL')")
    specimen_collected_at: Optional[datetime] = Field(
        None, description="Timestamp when specimen was drawn"
    )
    laboratory_id: Optional[str] = Field(None, description="Identifier of executing laboratory")
    lab_changed: bool = Field(
        False, description="Flag indicating if analyzer/lab changed from previous draw"
    )


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
    rationale_text: Optional[str] = Field(
        None, description="Clinician justification for alert disposition"
    )
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
    reason: Optional[str] = Field(
        None, description="Optional clinical note explaining state transition"
    )


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


class SymptomCreateRequest(BaseModel):
    symptom_name: str = Field(..., description="Name/category of symptom (e.g. bone_pain, fatigue)")
    severity: int = Field(
        1, ge=1, le=4, description="Severity grade (1=Mild, 2=Moderate, 3=Severe, 4=Very Severe)"
    )
    notes: Optional[str] = Field(None, description="Patient/caregiver description or notes")
    input_modality: str = Field("text", description="Input modality e.g. text or voice")
    recorded_at: Optional[datetime] = Field(None, description="Timestamp of symptom experience")


class SymptomResponse(BaseModel):
    id: str
    patient_id: str
    symptom_name: str
    severity: int
    notes: Optional[str] = None
    input_modality: str = "text"
    recorded_at: datetime
    created_at: datetime
    synthetic: bool = True


class CaregiverShareCreateRequest(BaseModel):
    caregiver_name: str = Field(..., description="Name of the family caregiver")
    relationship_type: str = Field(
        "caregiver", description="Relationship (e.g. daughter, spouse, sibling)"
    )
    scope: str = Field("view_summary", description="Access scope: view_summary or full_history")
    expires_in_days: int = Field(30, ge=1, le=365, description="Validity period in days")


class CaregiverShareResponse(BaseModel):
    id: str
    patient_id: str
    share_token: str
    caregiver_name: str
    relationship_type: str
    scope: str
    status: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime
    synthetic: bool = True


class SecondLookCreateRequest(BaseModel):
    observation_id: str = Field(..., description="ID of observation to be re-evaluated")
    patient_notes: Optional[str] = Field(
        None, description="Questions or context from patient/caregiver"
    )
    requested_action: Optional[str] = Field(
        "repeat_lab_review", description="Requested clinical review action"
    )


class SecondLookResponse(BaseModel):
    task_id: str
    observation_id: str
    patient_id: str
    analyte_code: str
    value: float
    unit: str
    plausibility_status: str
    status: str
    notes: Optional[str] = None
    created_at: datetime
    synthetic: bool = True


class DisclosureUnlockRequest(BaseModel):
    reason: Optional[str] = Field(
        "patient_opt_in_reveal", description="Reason for unlocking bad news / sensitive result"
    )


class DisclosureUnlockResponse(BaseModel):
    unlocked: bool
    unlocked_at: datetime
    message: str
    synthetic: bool = True


class PlainLanguageExplainerResponse(BaseModel):
    observation_id: str
    patient_id: str
    analyte_code: str
    verdict: str
    verbal_band: str
    headline: str
    what_this_means: str
    recommended_action: str
    questions_to_ask_your_doctor: List[str]
    flesch_kincaid_grade_level: float
    word_count: int
    verified: bool = True
    synthetic: bool = True
