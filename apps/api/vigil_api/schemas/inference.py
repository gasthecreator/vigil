"""Pydantic schemas for lab submission, abstention, trajectory, and triage."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class LabSubmissionResponse(BaseModel):
    status: Literal["recorded", "unavailable"]
    patient_id: str
    lab_result_id: str
    message: str
    outputs_withheld: bool
    calculated_metastasis_risk: None
    triage_flag: None

    model_config = ConfigDict(from_attributes=True)


class TrajectoryPoint(BaseModel):
    lab_id: str
    date_drawn: datetime
    alt_level: float
    ast_level: float
    creatinine: float
    ca_15_3: float
    wbc_count: float
    calculated_metastasis_risk: float | None
    ci_lower: float | None
    ci_upper: float | None
    ca153_velocity_pct: Optional[float] = 0.0
    alt_velocity_pct: Optional[float] = 0.0
    triage_flag: bool | None
    justification_text: str

    model_config = ConfigDict(from_attributes=True)


class TriageQueueItem(BaseModel):
    patient_id: str
    age: int
    status: str
    tumor_stage: Optional[int] = None
    subtype: str = "Unknown"
    latest_risk: float | None
    triage_flag: bool | None
    latest_justification: str
    target_organ_susceptibility_vector: dict[str, float] | None
    last_lab_date: Optional[datetime] = None
    total_labs: int = 0
    action_urgency: float | None
    urgency_breakdown: dict[str, float] | None


class SimulationRequest(BaseModel):
    hypothetical_lab: dict[str, float]


class SimulationResponse(BaseModel):
    status: Literal["abstained"]
    message: str
    projected_risk: float | None
    triage_flag: bool | None
    justification_text: str
    delta_risk: float | None
