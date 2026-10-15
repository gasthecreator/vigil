"""
contracts.loaders.mimic_loader

Cohort builder contract and schema validation for MIMIC-IV oncology laboratory trajectories.
Filters dense ICU records by malignant neoplasm diagnosis codes and documents ICU bias.
"""

from pathlib import Path
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

# Default malignant neoplasm ICD codes (ICD-9 174.* breast, ICD-10 C50.* breast)
DEFAULT_BREAST_CANCER_ICD = ["1749", "1740", "1741", "1748", "C50911", "C50912", "C50919", "C50411"]


class MIMICAdmissionRecord(BaseModel):
    subject_id: int = Field(..., ge=1)
    hadm_id: int = Field(..., ge=1)
    admittime: str
    dischtime: str
    hospital_expire_flag: int = Field(..., ge=0, le=1)


class MIMICLabRecord(BaseModel):
    labevent_id: int = Field(..., ge=1)
    subject_id: int = Field(..., ge=1)
    hadm_id: Optional[int] = None
    itemid: int = Field(..., ge=1)
    charttime: str
    valuenum: float
    valueuom: str
    flag: Optional[str] = None


def build_mimic_cancer_cohort(
    admissions_file: str | Path,
    diagnoses_file: str | Path,
    labevents_file: str | Path,
    cancer_icd_codes: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Constructs a cancer-specific longitudinal laboratory cohort from MIMIC-IV tables.
    Filters admissions by malignant neoplasm ICD codes and joins dense lab time series.
    """
    adm_p = Path(admissions_file)
    diag_p = Path(diagnoses_file)
    lab_p = Path(labevents_file)

    if not adm_p.exists():
        raise FileNotFoundError(f"Admissions file not found: {adm_p}")
    if not diag_p.exists():
        raise FileNotFoundError(f"Diagnoses file not found: {diag_p}")
    if not lab_p.exists():
        raise FileNotFoundError(f"Labevents file not found: {lab_p}")

    target_icd = set(cancer_icd_codes or DEFAULT_BREAST_CANCER_ICD)

    diag_df = pd.read_csv(diag_p, dtype={"icd_code": str})
    cancer_diag = diag_df[diag_df["icd_code"].isin(target_icd)]
    cancer_subjects = set(cancer_diag["subject_id"].unique())

    if not cancer_subjects:
        return pd.DataFrame()

    adm_df = pd.read_csv(adm_p)
    cancer_adm = adm_df[adm_df["subject_id"].isin(cancer_subjects)]

    lab_df = pd.read_csv(lab_p)
    cancer_labs = lab_df[lab_df["subject_id"].isin(cancer_subjects)]

    # Validate lab records
    clean_labs = []
    raw_labs = cancer_labs.to_dict(orient="records")
    for idx, raw_row in enumerate(raw_labs):
        clean_row = {k: (None if pd.isna(v) else v) for k, v in raw_row.items()}
        try:
            clean_labs.append(MIMICLabRecord(**clean_row).model_dump())
        except ValidationError as e:
            raise ValueError(f"MIMIC lab validation failed at row {idx}: {e}")

    merged = pd.merge(
        pd.DataFrame(clean_labs),
        cancer_adm[["subject_id", "hadm_id", "admittime", "hospital_expire_flag"]],
        on=["subject_id", "hadm_id"],
        how="left",
    )
    return merged
