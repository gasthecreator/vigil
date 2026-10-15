"""Pydantic schemas for Risk Inference, Trajectory, and Triage Queue."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class RiskInferenceResponse(BaseModel):
    id: str
    patient_id: str
    lab_result_id: str
    calculated_metastasis_risk: float = Field(..., ge=0.0, le=1.0)
    triage_flag: bool
    justification_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrajectoryPoint(BaseModel):
    lab_id: str
    date_drawn: datetime
    alt_level: float
    ast_level: float
    creatinine: float
    ca_15_3: float
    wbc_count: float
    calculated_metastasis_risk: float
    ci_lower: Optional[float] = 0.0
    ci_upper: Optional[float] = 1.0
    ca153_velocity_pct: Optional[float] = 0.0
    alt_velocity_pct: Optional[float] = 0.0
    triage_flag: bool
    justification_text: str

    model_config = ConfigDict(from_attributes=True)


class TriageQueueItem(BaseModel):
    patient_id: str
    age: int
    status: str
    tumor_stage: Optional[int] = None
    subtype: str = "Unknown"
    latest_risk: float
    triage_flag: bool
    latest_justification: str
    target_organ_susceptibility_vector: Optional[dict[str, float]] = None
    last_lab_date: Optional[datetime] = None
    total_labs: int = 0


class SimulationRequest(BaseModel):
    hypothetical_lab: dict[str, float]


class SimulationResponse(BaseModel):
    projected_risk: float
    triage_flag: bool
    justification_text: str
    delta_risk: float
