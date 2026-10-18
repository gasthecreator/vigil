"""
contracts.loaders.metabric_loader

Loader contract and schema validation for METABRIC clinical files from cBioPortal.

SUPERSEDED for real data by ``contracts.loaders.cbioportal`` (per-row rejection
reports, real cBioPortal column names, tested on the files published by the
study; see ``scripts/fetch_public_clinical.py`` and the dataset card in
``data/dataset_cards/``). This module validates only the small synthetic fixture
in ``data/fixtures/`` and is kept so that its existing tests keep running; do not
use it on downloaded data.
"""

from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class METABRICRecord(BaseModel):
    PATIENT_ID: str = Field(..., description="Unique METABRIC patient identifier")
    AGE_AT_DIAGNOSIS: float = Field(..., ge=18.0, le=115.0)
    ER_STATUS: str = Field(..., description="Positive / Negative")
    PR_STATUS: str = Field(..., description="Positive / Negative")
    HER2_STATUS: str = Field(..., description="Positive / Negative")
    CLAUDIN_SUBTYPE: str = Field(..., description="LumA, LumB, Her2, Basal, Normal-like")
    NOTTINGHAM_PROGNOSTIC_INDEX: float = Field(..., ge=0.0)
    TUMOUR_STAGE: str = Field(..., description="Stage I-IV")
    OS_MONTHS: float = Field(..., ge=0.0)
    OS_STATUS: str = Field(..., description="LIVING / DECEASED")
    RFS_MONTHS: float = Field(..., ge=0.0)
    RFS_STATUS: str = Field(..., description="Relapse status indicator")


def load_metabric_dataset(filepath: str | Path) -> pd.DataFrame:
    """
    Loads and validates a METABRIC clinical extract CSV.
    """
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"METABRIC file not found: {p}")

    df = pd.read_csv(p)
    records = df.to_dict(orient="records")

    validated_rows = []
    for idx, row in enumerate(records):
        try:
            rec = METABRICRecord(**row)
            validated_rows.append(rec.model_dump())
        except ValidationError as e:
            raise ValueError(f"METABRIC validation failed at row {idx}: {e}")

    return pd.DataFrame(validated_rows)
