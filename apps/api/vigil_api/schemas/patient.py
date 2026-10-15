"""Pydantic schemas for Patient."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientCreate(BaseModel):
    age: int = Field(..., ge=18, le=120, description="Patient age in years")
    status: str = Field(default="active", description="Clinical surveillance status")


class PatientResponse(BaseModel):
    id: str
    age: int
    created_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)
