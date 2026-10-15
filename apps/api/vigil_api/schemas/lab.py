"""Pydantic schemas for Laboratory Results."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LabResultCreate(BaseModel):
    date_drawn: Optional[datetime] = Field(
        default=None, description="Date and time blood specimen was drawn"
    )
    alt_level: float = Field(..., ge=1.0, le=1000.0, description="Alanine Transaminase (U/L)")
    ast_level: float = Field(..., ge=1.0, le=1000.0, description="Aspartate Transaminase (U/L)")
    creatinine: float = Field(..., ge=0.1, le=20.0, description="Serum Creatinine (mg/dL)")
    ca_15_3: float = Field(..., ge=1.0, le=2000.0, description="Cancer Antigen 15-3 (U/mL)")
    wbc_count: float = Field(..., ge=0.2, le=100.0, description="White Blood Cell count (x10^9/L)")


class LabResultResponse(BaseModel):
    id: str
    patient_id: str
    date_drawn: datetime
    alt_level: float
    ast_level: float
    creatinine: float
    ca_15_3: float
    wbc_count: float

    model_config = ConfigDict(from_attributes=True)
