"""
contracts.loaders.tcga_loader

Loader contract and schema validation for TCGA-BRCA clinical data files from NCI GDC.
"""

from pathlib import Path
from typing import Optional
import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class TCGARecord(BaseModel):
    bcr_patient_barcode: str = Field(..., description="TCGA barcode e.g. TCGA-A2-A0T0")
    age_at_initial_pathologic_diagnosis: int = Field(..., ge=18, le=115)
    gender: str = Field(..., description="Biological sex (FEMALE/MALE)")
    ajcc_pathologic_tumor_stage: str = Field(..., description="AJCC stage")
    er_status_by_ihc: str = Field(..., description="Positive / Negative")
    pr_status_by_ihc: str = Field(..., description="Positive / Negative")
    her2_status_by_ihc: str = Field(..., description="Positive / Negative / Equivocal")
    days_to_last_followup: Optional[float] = Field(None, ge=0)
    days_to_death: Optional[float] = Field(None, ge=0)
    days_to_new_tumor_event_after_initial_treatment: Optional[float] = Field(None, ge=0)
    new_neoplasm_event_type: Optional[str] = Field(None)


def load_tcga_dataset(filepath: str | Path) -> pd.DataFrame:
    """
    Loads and validates a TCGA-BRCA clinical CSV extract.
    """
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"TCGA-BRCA file not found: {p}")

    df = pd.read_csv(p)
    raw_records = df.to_dict(orient="records")
    validated_rows = []
    for idx, raw_row in enumerate(raw_records):
        clean_row = {k: (None if pd.isna(v) else v) for k, v in raw_row.items()}
        try:
            rec = TCGARecord(**clean_row)
            validated_rows.append(rec.model_dump())
        except ValidationError as e:
            raise ValueError(f"TCGA-BRCA validation failed at row {idx}: {e}")

    return pd.DataFrame(validated_rows)
