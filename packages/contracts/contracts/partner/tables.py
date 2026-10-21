"""Table specifications of the partner extraction (docs/clinical/PARTNERSHIP/DATA-DICTIONARY.md).

One place defines the columns, types, enumerations and ranges so that the loader, the rejection report and the
documentation are checked against the same text. Dates are *relative integer days*; absolute dates are refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple


@dataclass(frozen=True)
class Col:
    name: str
    kind: str  # "str" | "int" | "float" | "bool" | "enum" | "id"
    required: bool = True
    enum: Tuple[str, ...] = ()
    lo: Optional[float] = None
    hi: Optional[float] = None
    conditional: bool = (
        False  # required only when another rule says so (checked in cross-field rules)
    )


@dataclass(frozen=True)
class Table:
    name: str
    columns: Tuple[Col, ...]
    key: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def column_names(self) -> Tuple[str, ...]:
        return tuple(c.name for c in self.columns)


def _tri(name: str) -> Col:
    return Col(name, "enum", enum=("POSITIVE", "NEGATIVE", "EQUIVOCAL", "UNKNOWN"))


def _flag(name: str, required: bool = True, conditional: bool = False) -> Col:
    return Col(name, "bool", required=required, conditional=conditional)


PATIENTS = Table(
    "patients",
    (
        Col("patient_id", "id"),
        Col("age_at_diagnosis", "int", lo=18, hi=105),
        Col("menopausal_status", "enum", enum=("PRE", "PERI", "POST", "UNKNOWN")),
        Col(
            "vital_status", "enum", enum=("ALIVE", "DEAD_DISEASE", "DEAD_OTHER", "LOST_TO_FOLLOWUP")
        ),
        Col("days_to_last_followup", "int", lo=0),
        Col("days_to_death", "int", required=False, conditional=True, lo=0),
        Col("index_day", "int", lo=0),
    ),
    key=("patient_id",),
)

BASELINE_PROFILE = Table(
    "baseline_profile",
    (
        Col("patient_id", "id"),
        Col("histological_type", "enum", enum=("IDC", "ILC", "MUCINOUS", "METAPLASTIC", "OTHER")),
        Col("tumor_grade", "int", lo=1, hi=3),
        Col("stage_ajcc", "enum", enum=("I", "IIA", "IIB", "IIIA", "IIIB", "IIIC")),
        _tri("er_status"),
        _tri("pr_status"),
        _tri("her2_status"),
        _flag("has_hypertension"),
        _flag("renal_history"),
        Col("surgery_type", "enum", enum=("MRM", "BCS", "TOTAL_MASTECTOMY", "NONE")),
        _flag("chemotherapy_given"),
        _flag("endocrine_therapy"),
        _flag("radiotherapy_given"),
    ),
    key=("patient_id",),
)

LAB_OBSERVATIONS = Table(
    "lab_observations",
    (
        Col("patient_id", "id"),
        Col("observation_day", "int", lo=0, hi=3650),
        Col("analyte_code", "str"),  # LOINC
        Col("analyte_name", "str"),
        Col("value_numeric", "float", lo=0.0),
        Col("unit_ucum", "str"),
        Col("ref_low", "float", required=False),
        Col("ref_high", "float", required=False),
    ),
    key=("patient_id", "observation_day", "analyte_code"),
)

CLINICAL_OUTCOMES = Table(
    "clinical_outcomes",
    (
        Col("patient_id", "id"),
        _flag("recurrence_confirmed"),
        Col("recurrence_day", "int", required=False, conditional=True, lo=0),
        _flag("site_bone", required=False, conditional=True),
        _flag("site_liver", required=False, conditional=True),
        _flag("site_lung", required=False, conditional=True),
        _flag("site_brain", required=False, conditional=True),
        _flag("site_locoregional", required=False, conditional=True),
        Col(
            "confirmatory_modality",
            "enum",
            required=False,
            conditional=True,
            enum=("ULTRASOUND", "CT_SCAN", "MRI", "XRAY", "BONE_SCAN", "BIOPSY", "CLINICAL"),
        ),
        _flag("dismissed_prior_signal", required=False),
        _flag("restaging_imaging_done", required=False),
    ),
    key=("patient_id",),
)

TABLES: Sequence[Table] = (PATIENTS, BASELINE_PROFILE, LAB_OBSERVATIONS, CLINICAL_OUTCOMES)
TABLE_BY_NAME = {t.name: t for t in TABLES}

# Column names that indicate a direct identifier. Any file with one is refused before any row is read.
FORBIDDEN_COLUMN_FRAGMENTS: Tuple[str, ...] = (
    "name",
    "surname",
    "firstname",
    "lastname",
    "phone",
    "mobile",
    "tel",
    "email",
    "mail",
    "address",
    "street",
    "dob",
    "birth",
    "nin",
    "bvn",
    "ssn",
    "passport",
    "mrn",
    "hospital",
    "folder",
    "next_of_kin",
    "kin",
)
