from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PatientCreate(BaseModel):
    age: int = Field(..., ge=18, le=120, description="Patient age in years")
    status: str = Field(default="active", description="Clinical surveillance status")
    mrn: Optional[str] = Field(None, description="Medical Record Number (encrypted at rest)")
    external_id: Optional[str] = Field(None, description="External hospital system identifier (encrypted at rest)")


class PatientUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=18, le=120, description="Patient age in years")
    status: Optional[str] = Field(None, description="Clinical surveillance status")
    mrn: Optional[str] = Field(None, description="Medical Record Number (encrypted at rest)")
    external_id: Optional[str] = Field(None, description="External hospital system identifier (encrypted at rest)")


class PatientResponse(BaseModel):
    id: str
    age: int
    created_at: datetime
    status: str
    mrn: Optional[str] = None
    external_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
