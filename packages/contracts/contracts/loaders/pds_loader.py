"""
contracts.loaders.pds_loader

Loader contract and schema validation for Project Data Sphere CDISC SDTM domain tables (DM, LB).
"""

from pathlib import Path
from typing import Tuple, Union
import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class PDSDemographicRecord(BaseModel):
    USUBJID: str = Field(..., description="Unique Subject Identifier")
    AGE: int = Field(..., ge=18, le=115)
    SEX: str = Field(..., description="Biological sex (M/F)")
    ARM: str = Field(..., description="Trial Arm Description")
    RFSTDTC: str = Field(..., description="Reference Start Date (ISO 8601)")


class PDSLabRecord(BaseModel):
    USUBJID: str = Field(..., description="Unique Subject Identifier")
    LBTESTCD: str = Field(..., description="Lab Test Short Code (e.g. ALT, CA153)")
    LBTEST: str = Field(..., description="Lab Test Full Name")
    LBORRES: Union[str, float] = Field(..., description="Original Result Value")
    LBORRESU: str = Field(..., description="Original Result Unit")
    LBSTRESN: float = Field(..., description="Standard Numeric Result")
    LBSTRESU: str = Field(..., description="Standardized Result Unit")
    LBDTC: str = Field(..., description="Date/Time of Specimen Collection")
    VISITNUM: int = Field(..., ge=1, description="Protocol Visit Number")


def load_pds_dataset(
    dm_filepath: str | Path,
    lb_filepath: str | Path,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads and validates CDISC DM and LB datasets from Project Data Sphere extracts.
    """
    dm_p = Path(dm_filepath)
    lb_p = Path(lb_filepath)

    if not dm_p.exists():
        raise FileNotFoundError(f"PDS DM file not found: {dm_p}")
    if not lb_p.exists():
        raise FileNotFoundError(f"PDS LB file not found: {lb_p}")

    dm_df = pd.read_csv(dm_p)
    lb_df = pd.read_csv(lb_p)

    val_dm = []
    for idx, row in enumerate(dm_df.to_dict(orient="records")):
        try:
            val_dm.append(PDSDemographicRecord(**row).model_dump())
        except ValidationError as e:
            raise ValueError(f"PDS DM validation failed at row {idx}: {e}")

    val_lb = []
    for idx, row in enumerate(lb_df.to_dict(orient="records")):
        try:
            val_lb.append(PDSLabRecord(**row).model_dump())
        except ValidationError as e:
            raise ValueError(f"PDS LB validation failed at row {idx}: {e}")

    return pd.DataFrame(val_dm), pd.DataFrame(val_lb)
