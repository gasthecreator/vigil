"""
contracts.loaders.seer_loader

Loader contract and schema validation for SEER breast cancer registry tables.
Validates fields against official NCI SEER Research Data Dictionary.
"""

from pathlib import Path
from typing import Optional
import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class SEERRecord(BaseModel):
    SEER_ID: str = Field(..., description="Unique de-identified registry ID")
    AGE_DX: int = Field(..., ge=18, le=115, description="Age at diagnosis")
    YEAR_DX: int = Field(..., ge=1975, le=2026, description="Year of diagnosis")
    HISTOLOGY: int = Field(..., description="ICD-O-3 histology code")
    STAGE_GROUP: str = Field(..., description="AJCC stage group (Stage I-IV)")
    SUBTYPE: str = Field(..., description="Molecular subtype (HR+/HER2-, HER2+, TNBC)")
    MET_BONE: str = Field(..., description="Bone metastasis at diagnosis (Yes/No/Unknown)")
    MET_LIVER: str = Field(..., description="Liver metastasis at diagnosis (Yes/No/Unknown)")
    MET_LUNG: str = Field(..., description="Lung metastasis at diagnosis (Yes/No/Unknown)")
    MET_BRAIN: str = Field(..., description="Brain metastasis at diagnosis (Yes/No/Unknown)")
    SURVIVAL_MONTHS: int = Field(..., ge=0, description="Overall survival duration in months")
    VITAL_STATUS: str = Field(..., description="Vital status (Alive/Dead)")


def load_seer_dataset(filepath: str | Path) -> pd.DataFrame:
    """
    Loads and strictly validates a SEER registry extract CSV against SEERRecord schema.
    """
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"SEER data file not found: {p}")

    df = pd.read_csv(p)
    records = df.to_dict(orient="records")

    validated_rows = []
    for idx, row in enumerate(records):
        try:
            rec = SEERRecord(**row)
            validated_rows.append(rec.model_dump())
        except ValidationError as e:
            raise ValueError(f"SEER validation failed at row {idx}: {e}")

    return pd.DataFrame(validated_rows)
