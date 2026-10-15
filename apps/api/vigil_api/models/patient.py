"""SQLAlchemy 2.0 Relational Data Models for Sentinel Platform."""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship

from vigil_api.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    age = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="active", nullable=False)

    # Relationships
    baseline_profile = relationship("BaselineProfile", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="patient", cascade="all, delete-orphan", order_by="LabResult.date_drawn")
    risk_inferences = relationship("RiskInference", back_populates="patient", cascade="all, delete-orphan", order_by="RiskInference.created_at")


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

    # Relationship
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

    # Relationships
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

    # Relationships
    patient = relationship("Patient", back_populates="risk_inferences")
    lab_result = relationship("LabResult", back_populates="risk_inference")


# Compound index for fast triage sorting and lookups
Index("idx_patient_latest_risk", RiskInference.patient_id, RiskInference.calculated_metastasis_risk)
