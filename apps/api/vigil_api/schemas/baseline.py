"""Pydantic schemas for Baseline Profile."""

from pydantic import BaseModel, Field, ConfigDict


class TargetOrganVector(BaseModel):
    bone: float = Field(..., ge=0.0, le=1.0)
    liver: float = Field(..., ge=0.0, le=1.0)
    lung: float = Field(..., ge=0.0, le=1.0)
    brain: float = Field(..., ge=0.0, le=1.0)


class BaselineCreate(BaseModel):
    tumor_stage: int = Field(..., ge=1, le=4, description="Primary tumor stage (1-4)")
    er_status: bool = Field(..., description="Estrogen Receptor status (ER+/-)")
    pr_status: bool = Field(..., description="Progesterone Receptor status (PR+/-)")
    her2_status: bool = Field(..., description="HER2 receptor amplification status (HER2+/-)")
    has_hypertension: bool = Field(default=False, description="Hypertension comorbidity")
    renal_history: bool = Field(default=False, description="Chronic renal disease history")


class BaselineResponse(BaseModel):
    id: str
    patient_id: str
    tumor_stage: int
    er_status: bool
    pr_status: bool
    her2_status: bool
    has_hypertension: bool
    renal_history: bool
    target_organ_susceptibility_vector: TargetOrganVector

    model_config = ConfigDict(from_attributes=True)
