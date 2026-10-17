"""Data Model v2 for Vigil Precision Oncology Platform.

Implements Master Plan §6.0 (M0), §6.6 (M6), §9, §11, and Phase 5a.
Features:
  - Facility & Multi-Tenancy
  - Patient with explicit synthetic flag (Principle 1)
  - Unit-safe Observations linked to Analyte Registry
  - RiskAssessment with model versions, input hash, uncertainty, abstention
  - Check constraints enforcing the No-Dismissal Safety Invariant
  - Alert & AlertAcknowledgement with disposition tracking
  - FollowUpTask (M6 state machine) with escalation ladder
  - ConsentRecord for role-based consent evaluation
  - Hash-chained append-only AuditEvent
  - User and RBAC roles
"""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from vigil_api.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    CLINICIAN = "clinician"
    NURSE_CLERK = "nurse_clerk"
    QUALITY_LEAD = "quality_lead"
    ADMIN = "admin"
    PATIENT = "patient"
    CAREGIVER = "caregiver"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class AlertDisposition(str, enum.Enum):
    CONFIRMED_RECURRENCE = "confirmed_recurrence"
    FALSE_ALARM = "false_alarm"
    SAMPLE_REDRAW_ORDERED = "sample_redraw_ordered"
    CLINICAL_HOLD = "clinical_hold"
    OTHER = "other"


class FollowUpTaskType(str, enum.Enum):
    REPEAT_SPECIMEN = "repeat_specimen"
    IMAGING_REFERRAL = "imaging_referral"
    CLINICAL_REVIEW = "clinical_review"
    PATIENT_OUTREACH = "patient_outreach"


class FollowUpTaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    DECLINED_WITH_REASON = "declined_with_reason"
    TRANSFERRED = "transferred"
    CANCELLED_BY_CLINICIAN = "cancelled_by_clinician"
    LOST_TO_FOLLOW_UP_AFTER_N_ATTEMPTS = "lost_to_follow_up_after_N_attempts"
    CANCELLED = "cancelled"


# ==============================================================================
# 1. Facility & User Models
# ==============================================================================


class Facility(Base):
    __tablename__ = "facilities"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    country = Column(String(10), default="NG", nullable=False)
    tier = Column(String(50), default="tertiary", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    users = relationship("User", back_populates="facility")
    patients = relationship("Patient", back_populates="facility")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    role = Column(String(50), default=UserRole.CLINICIAN.value, nullable=False, index=True)
    facility_id = Column(String(36), ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    facility = relationship("Facility", back_populates="users")
    acknowledgements = relationship("AlertAcknowledgement", back_populates="user")


# ==============================================================================
# 2. Patient & Consent Models
# ==============================================================================


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    facility_id = Column(String(36), ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True, index=True)
    mrn = Column(String(100), nullable=True, index=True)
    external_id = Column(String(100), nullable=True, index=True)
    age = Column(Integer, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    biological_sex = Column(String(20), default="female", nullable=False)
    menopausal_status = Column(String(20), nullable=True)  # pre, post, peri
    primary_cancer_type = Column(String(100), default="breast", nullable=False)
    initial_stage = Column(String(20), nullable=True)  # I, II, III, IV
    receptor_er = Column(Boolean, nullable=True)
    receptor_pr = Column(Boolean, nullable=True)
    receptor_her2 = Column(Boolean, nullable=True)
    primary_diagnosis_date = Column(DateTime, nullable=True)
    synthetic = Column(Boolean, default=True, nullable=False, index=True)  # Principle 1
    status = Column(String(50), default="active", nullable=False, index=True)
    detector_state = Column(JSON, nullable=True)  # Persisted K2 SequentialDetector state
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    facility = relationship("Facility", back_populates="patients")
    consent_records = relationship("ConsentRecord", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="patient", cascade="all, delete-orphan", order_by="Observation.specimen_collected_at")
    risk_assessments = relationship("RiskAssessment", back_populates="patient", cascade="all, delete-orphan", order_by="RiskAssessment.assessment_date")
    alerts = relationship("Alert", back_populates="patient", cascade="all, delete-orphan")
    follow_up_tasks = relationship("FollowUpTask", back_populates="patient", cascade="all, delete-orphan")

    # Legacy prototype relationships for backward compatibility
    baseline_profile = relationship("BaselineProfile", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="patient", cascade="all, delete-orphan", order_by="LabResult.date_drawn")
    risk_inferences = relationship("RiskInference", back_populates="patient", cascade="all, delete-orphan")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(100), default="surveillance_monitoring", nullable=False)
    granted = Column(Boolean, default=True, nullable=False)
    granted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    scope = Column(String(100), default="full", nullable=False)

    patient = relationship("Patient", back_populates="consent_records")


# ==============================================================================
# 3. Clinical Observation & Risk Assessment Models (No-Dismissal Invariant)
# ==============================================================================


class Observation(Base):
    __tablename__ = "observations"

    __table_args__ = (
        CheckConstraint("status != 'dismissed'", name="chk_observation_no_dismissal"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    analyte_code = Column(String(50), nullable=False, index=True)  # validated via vigil_core.analytes
    value = Column(Float, nullable=False)  # Canonical value in canonical UCUM unit
    unit = Column(String(50), nullable=False)  # Canonical UCUM unit string
    specimen_collected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    result_received_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    laboratory_id = Column(String(100), nullable=True)
    plausibility_status = Column(String(50), nullable=False, default="valid_normal")
    raw_value = Column(Float, nullable=False)
    raw_unit = Column(String(50), nullable=False)
    status = Column(String(50), default="valid", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="observations")
    risk_assessment = relationship("RiskAssessment", back_populates="observation", uselist=False)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    __table_args__ = (
        CheckConstraint("adjudicated_action != 'dismissed'", name="chk_risk_no_dismissal"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    observation_id = Column(String(36), ForeignKey("observations.id", ondelete="SET NULL"), nullable=True, index=True)
    assessment_date = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    model_versions = Column(JSON, nullable=False)  # e.g. {"M3": "1.0", "K2": "1.0", "M5": "1.0"}
    input_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of inputs
    score = Column(Float, nullable=False)  # e.g. p_real or e-process score
    risk_tier = Column(String(50), default="low", nullable=False, index=True)
    uncertainty = Column(JSON, nullable=True)  # confidence/credible intervals
    abstention = Column(Boolean, default=False, nullable=False)
    abstention_reason = Column(String(500), nullable=True)
    adjudicated_action = Column(String(50), nullable=False, default="explained")  # explained, needs_repeat, escalate
    clinical_note = Column(Text, nullable=True)  # Provenance-verified narrative (M5)
    rationale_facts = Column(JSON, nullable=True)  # Structured rationale facts from M3
    k2_state_snapshot = Column(JSON, nullable=True)  # Detector state snapshot
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="risk_assessments")
    observation = relationship("Observation", back_populates="risk_assessment")
    alerts = relationship("Alert", back_populates="risk_assessment")


# ==============================================================================
# 4. Alerts & Actionable Follow-Up Tasks (M6 State Machine)
# ==============================================================================


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_assessment_id = Column(String(36), ForeignKey("risk_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False, index=True)  # biomarker_spike, lab_error_repeat, sequential_divergence
    severity = Column(String(50), default=AlertSeverity.WARNING.value, nullable=False, index=True)
    trigger_reason = Column(String(500), nullable=False)
    status = Column(String(50), default=AlertStatus.OPEN.value, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="alerts")
    risk_assessment = relationship("RiskAssessment", back_populates="alerts")
    acknowledgements = relationship("AlertAcknowledgement", back_populates="alert", cascade="all, delete-orphan")
    follow_up_tasks = relationship("FollowUpTask", back_populates="alert")


class AlertAcknowledgement(Base):
    __tablename__ = "alert_acknowledgements"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    alert_id = Column(String(36), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    disposition = Column(String(100), nullable=False)  # confirmed_recurrence, false_alarm, sample_redraw_ordered, clinical_hold, other
    rationale_text = Column(Text, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    alert = relationship("Alert", back_populates="acknowledgements")
    user = relationship("User", back_populates="acknowledgements")


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id = Column(String(36), ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True)
    task_type = Column(String(100), nullable=False, index=True)  # repeat_specimen, imaging_referral, clinical_review, patient_outreach
    status = Column(String(50), default=FollowUpTaskStatus.PENDING.value, nullable=False, index=True)
    due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    escalation_level = Column(Integer, default=0, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="follow_up_tasks")
    alert = relationship("Alert", back_populates="follow_up_tasks")


# ==============================================================================
# 5. Hash-Chained Append-Only Audit Event Model
# ==============================================================================


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    actor_id = Column(String(100), nullable=False, index=True)
    actor_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False, index=True)  # e.g. "observation.create", "patient.read"
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), nullable=False, index=True)
    details = Column(JSON, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    curr_hash = Column(String(64), nullable=False, index=True)


def calculate_audit_hash(
    prev_hash: str,
    timestamp: datetime,
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Dict[str, Any],
) -> str:
    """Compute SHA-256 hash for immutable hash-chain audit log entry."""
    if isinstance(timestamp, datetime):
        ts_utc = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        ts_str = ts_utc.astimezone(timezone.utc).isoformat()
    else:
        ts_str = str(timestamp)

    payload = {
        "prev_hash": prev_hash,
        "timestamp": ts_str,
        "actor_id": str(actor_id),
        "actor_role": str(actor_role),
        "action": str(action),
        "resource_type": str(resource_type),
        "resource_id": str(resource_id),
        "details": details,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ==============================================================================
# 6. Legacy Models (Preserved for compatibility)
# ==============================================================================


class BaselineProfile(Base):
    __tablename__ = "baseline_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    tumor_stage = Column(Integer, nullable=False)
    er_status = Column(Boolean, nullable=False)
    pr_status = Column(Boolean, nullable=False)
    her2_status = Column(Boolean, nullable=False)
    has_hypertension = Column(Boolean, default=False, nullable=False)
    renal_history = Column(Boolean, default=False, nullable=False)
    target_organ_susceptibility_vector = Column(JSON, nullable=False)

    patient = relationship("Patient", back_populates="baseline_profile")


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    date_drawn = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    alt_level = Column(Float, nullable=False)
    ast_level = Column(Float, nullable=False)
    creatinine = Column(Float, nullable=False)
    ca_15_3 = Column(Float, nullable=False)
    wbc_count = Column(Float, nullable=False)

    patient = relationship("Patient", back_populates="lab_results")
    risk_inference = relationship("RiskInference", back_populates="lab_result", uselist=False, cascade="all, delete-orphan")


class RiskInference(Base):
    __tablename__ = "risk_inferences"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    lab_result_id = Column(String(36), ForeignKey("lab_results.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    calculated_metastasis_risk = Column(Float, nullable=False, index=True)
    triage_flag = Column(Boolean, nullable=False, index=True)
    justification_text = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="risk_inferences")
    lab_result = relationship("LabResult", back_populates="risk_inference")


# Compound index for fast triage sorting and lookups
Index("idx_patient_latest_risk", RiskInference.patient_id, RiskInference.calculated_metastasis_risk)
