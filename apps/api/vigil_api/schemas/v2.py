"""Pydantic v2 schemas for Vigil Precision Oncology Platform."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

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
    share_token: Optional[str] = None
    token_preview: str
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


class DisclosureReleaseRequest(BaseModel):
    reason: Optional[str] = Field(
        "Patient requested release of withheld diagnostic result",
        description="Reason or patient note for requesting clinician release",
    )


class DisclosureReleaseRequestResponse(BaseModel):
    requested: bool = True
    task_id: str
    message: str
    synthetic: bool = True


class DisclosureLockRequest(BaseModel):
    reason: Optional[str] = Field(
        "Clinician re-locked disclosure", description="Reason for re-locking disclosure"
    )


class DisclosureLockResponse(BaseModel):
    locked: bool = True
    locked_at: datetime
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


# ==============================================================================
# Treatment Continuity & Radiotherapy Triage Schemas (M7)
# ==============================================================================


class LinacMachineResponse(BaseModel):
    id: str
    facility_id: Optional[str] = None
    machine_name: str
    daily_slot_capacity: int
    status: str
    downtime_started_at: Optional[datetime] = None
    expected_return_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    synthetic: bool = True


class LinacMachineStatusUpdate(BaseModel):
    status: str = Field(..., description="Machine status: operational, down, maintenance")
    expected_return_at: Optional[datetime] = Field(
        None, description="Expected time machine will return to operational status"
    )
    reason: Optional[str] = Field(None, description="Reason for downtime or maintenance")


class RadiotherapyCourseCreate(BaseModel):
    patient_id: str
    clinical_context: str = Field(
        "adjuvant_post_lumpectomy",
        description="Clinical context: adjuvant_post_lumpectomy, adjuvant_post_mastectomy, curative_tnbc, palliative_bone_brain",
    )
    total_fractions: int = Field(15, ge=1, le=40)
    prescribed_start_date: datetime
    urgency_tier: str = Field("routine", description="Urgency tier: emergency, urgent, routine")
    assigned_machine_id: Optional[str] = None
    baseline_subgroup: Optional[str] = None


class RadiotherapyCourseResponse(BaseModel):
    id: str
    patient_id: str
    assigned_machine_id: Optional[str] = None
    clinical_context: str
    total_fractions: int
    fractions_delivered: int
    prescribed_start_date: datetime
    scheduled_start_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    urgency_tier: str
    status: str
    baseline_subgroup: Optional[str] = None
    current_delay_days: int = 0
    expected_excess_harm: float = 0.0
    created_at: datetime
    updated_at: datetime
    synthetic: bool = True


class DelayLedgerEntryResponse(BaseModel):
    id: str
    patient_id: str
    course_id: str
    delay_days: int
    reason: str
    marginal_harm: Optional[float] = None
    moved_from_date: Optional[datetime] = None
    moved_to_date: datetime
    clinician_overridden: bool = False
    recorded_by: str = "system_cp_sat"
    created_at: datetime
    synthetic: bool = True


class ScheduleSolveRequest(BaseModel):
    """Request a schedule proposal.

    ``method`` defaults to the explainable urgency ranking (ADR-0019). The CP-SAT
    optimiser is a research module: it is only available to
    administrators (or when the deployment sets ``VIGIL_ENABLE_RESEARCH_SCHEDULER=1``)
    and is always labelled ``unvalidated in simulation``. ``fairness_disparity_bound``,
    ``max_wait_days`` and ``stability_penalty`` apply to the CP-SAT method only.
    """

    method: Literal["urgency_ranking", "cpsat_research"] = "urgency_ranking"
    horizon_days: int = Field(30, ge=5, le=60)
    fairness_disparity_bound: float = Field(5.0, ge=0.5, le=30.0)
    max_wait_days: int = Field(45, ge=5, le=120)
    stability_penalty: float = Field(0.01, ge=0.0)


class ScheduleAssignment(BaseModel):
    patient_id: str
    course_id: str
    machine_id: str
    start_day: int
    scheduled_date: datetime
    fractions: int
    context: str
    delay_days: int
    marginal_harm: float
    explanation: str
    is_moved: bool = False
    priority_rank: Optional[int] = None  # 1 = served first (urgency ranking only)


class ScheduleSolveResponse(BaseModel):
    status: str
    solver_time_seconds: float
    total_excess_harm: float
    mean_delay_days: float
    max_delay_days: int
    fairness_disparity: float
    assignments: List[ScheduleAssignment]
    unassigned_patient_ids: List[str]
    patients_included: int = 0
    patients_unconsented_included: int = 0
    method: str = "urgency_ranking"
    method_label: str = "Explainable urgency ranking"
    fairness_bound_enforced: bool = False
    warnings: List[str] = Field(default_factory=list)
    validation_status: str = "unvalidated in simulation"
    synthetic: bool = True


class ScheduleConfirmRequest(BaseModel):
    assignments: List[ScheduleAssignment]
    reason: Optional[str] = Field(
        "Clinician approved schedule reallocation",
        description="Clinical rationale for confirming the schedule reallocation",
    )


class ScheduleConfirmResponse(BaseModel):
    confirmed: bool = True
    ledger_entries_created: int
    audit_event_id: str
    message: str
    synthetic: bool = True


class PatientDelayNoticeResponse(BaseModel):
    patient_id: str
    has_active_treatment: bool
    course_id: Optional[str] = None
    clinical_context: Optional[str] = None
    total_delay_days: int = 0
    machine_name: Optional[str] = None
    machine_status: Optional[str] = None
    expected_start_date: Optional[datetime] = None
    plain_language_notice: str
    delay_history: List[DelayLedgerEntryResponse] = []
    synthetic: bool = True


# ==============================================================================
# 8. Missed-Signal Quality Audit Schemas (M10)
# ==============================================================================


class StratumAuditMetricResponse(BaseModel):
    stratum_name: str
    total_signals: Union[int, str]
    action_not_recorded_count: Union[int, str]
    action_not_recorded_rate: Optional[float] = None
    is_suppressed: bool = False


class QualityAuditRequest(BaseModel):
    facility_id: Optional[str] = Field(
        None, description="Optional facility identifier to filter trajectories"
    )
    lookback_days: int = Field(
        365, ge=30, le=3650, description="Lookback window in days for surveillance audit"
    )
    n_bootstrap: int = Field(
        1000, ge=100, le=5000, description="Bootstrap iterations for confidence intervals"
    )
    include_synthetic_benchmark: bool = Field(
        False,
        description="Run the audit on the built-in SYNTHETIC benchmark cohort only (never mixed with facility data)",
    )


class QualityAuditResponse(BaseModel):
    audit_id: str
    facility_id: Optional[str] = None
    total_patients_audited: int
    total_signals_detected: int
    total_action_recorded: int
    total_action_not_recorded: int
    overall_action_not_recorded_rate: float
    overall_bootstrap_ci_95: List[float]
    subgroup_breakdown: Dict[str, StratumAuditMetricResponse]
    subtype_breakdown: Dict[str, StratumAuditMetricResponse]
    stage_breakdown: Dict[str, StratumAuditMetricResponse]
    suppressed_strata_count: int
    register_audit_verified: bool = True
    narrative_summary: str
    synthetic: bool = True
