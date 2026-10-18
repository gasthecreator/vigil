"""METABRIC and TCGA-BRCA (PanCancer Atlas) clinical data in the cBioPortal clinical-file format.

Real files differ from the older fixtures of this package: the attribute is ``NPI`` (not
``NOTTINGHAM_PROGNOSTIC_INDEX``), receptor status and stage are *sample* attributes, ``OS_STATUS`` reads
``1:DECEASED`` / ``0:LIVING``, and TCGA relapse is ``DFS_STATUS`` (``1:Recurred/Progressed``). Attribute lists were
read from ``/api/studies/<id>/clinical-attributes`` of cbioportal.org (see ``docs/evidence/excerpts``).

Input: a patient file and a sample file, tab-separated, attribute identifiers in the header, ``#`` metadata lines
allowed (the datahub download format), or the same shape written by ``scripts/fetch_public_clinical.py``.
Output: ``(DataFrame, report)``. A row that cannot be validated is rejected with a code and counted; the loader never
raises on a bad row and never repairs one. The report never contains raw cell values.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

NULL = {
    "",
    "NA",
    "N/A",
    "[NOT AVAILABLE]",
    "[NOT APPLICABLE]",
    "[UNKNOWN]",
    "[NOT EVALUATED]",
    "NAN",
    "NONE",
    "NULL",
}


@dataclass(frozen=True)
class StudySpec:
    name: str
    patient_attrs: Dict[str, str]  # canonical field -> cBioPortal attribute id (patient file)
    sample_attrs: Dict[str, str]  # canonical field -> attribute id (sample file)
    relapse_months: Optional[str]
    relapse_status: Optional[str]
    stage_map: Callable[[str], Optional[str]]
    age_range: Tuple[float, float] = (18.0, 115.0)


def _stage_numeric(v: str) -> Optional[str]:
    return {"0": "0", "1": "I", "2": "II", "3": "III", "4": "IV"}.get(v.strip())


def _stage_ajcc(v: str) -> Optional[str]:
    s = v.strip().upper().replace("STAGE ", "")
    for roman in ("IV", "III", "II", "I", "X"):
        if s.startswith(roman):
            return roman if roman != "X" else None
    return None


METABRIC = StudySpec(
    "METABRIC",
    {
        "age": "AGE_AT_DIAGNOSIS",
        "sex": "SEX",
        "subtype": "CLAUDIN_SUBTYPE",
        "os_months": "OS_MONTHS",
        "os_status": "OS_STATUS",
        "menopausal_state": "INFERRED_MENOPAUSAL_STATE",
        "npi": "NPI",
    },
    {
        "er": "ER_STATUS",
        "pr": "PR_STATUS",
        "her2": "HER2_STATUS",
        "grade": "GRADE",
        "stage": "TUMOR_STAGE",
    },
    "RFS_MONTHS",
    "RFS_STATUS",
    _stage_numeric,
)
TCGA_BRCA = StudySpec(
    "TCGA-BRCA",
    {
        "age": "AGE",
        "sex": "SEX",
        "subtype": "SUBTYPE",
        "os_months": "OS_MONTHS",
        "os_status": "OS_STATUS",
        "stage": "AJCC_PATHOLOGIC_TUMOR_STAGE",
    },
    {"grade": "GRADE"},
    "DFS_MONTHS",
    "DFS_STATUS",
    _stage_ajcc,
)
STUDIES = {"METABRIC": METABRIC, "TCGA-BRCA": TCGA_BRCA}

ROW_CODES = (
    "MISSING_REQUIRED",
    "BAD_TYPE",
    "OUT_OF_RANGE",
    "BAD_ENUM",
    "DUPLICATE_PATIENT",
    "NO_SAMPLE_ROW",
)


def read_clinical_file(path: Path) -> pd.DataFrame:
    """Tab-separated clinical file; ``#`` metadata lines skipped; every value kept as text."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not lines:
        raise ValueError(f"{path}: no header row")
    return pd.read_csv(
        io.StringIO("\n".join(lines)),
        sep="\t",
        dtype=str,
        keep_default_na=False,
        quoting=csv.QUOTE_NONE,
    )


def _clean(v: Any) -> Optional[str]:
    s = "" if v is None else str(v).strip()
    return None if s.upper() in NULL else s


def _event(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    head = v.split(":", 1)[0].strip()
    return int(head) if head in ("0", "1") else None


def _num(v: Optional[str]) -> Tuple[Optional[float], bool]:
    """(value, ok). ``ok`` is False for non-numeric text; a null is ``(None, True)``."""
    if v is None:
        return None, True
    try:
        f = float(v)
    except ValueError:
        return None, False
    return (f, True) if f == f and f not in (float("inf"), float("-inf")) else (None, False)


def load_study(
    study: str, patient_file: Path, sample_file: Optional[Path] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    spec = STUDIES[study]
    pat = read_clinical_file(patient_file)
    smp = read_clinical_file(sample_file) if sample_file is not None else None
    rejections: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    if "PATIENT_ID" not in pat.columns:
        raise ValueError("patient file has no PATIENT_ID column")
    missing_cols = [
        a
        for a in spec.patient_attrs.values()
        if a not in pat.columns and a not in ("SEX", "NPI", "INFERRED_MENOPAUSAL_STATE")
    ]
    if missing_cols:
        raise ValueError(
            f"patient file lacks required attribute(s): {', '.join(sorted(missing_cols))}"
        )
    sample_by_patient: Dict[str, Dict[str, Any]] = {}
    multi = 0
    if smp is not None and "PATIENT_ID" in smp.columns:
        sort_col = "SAMPLE_ID" if "SAMPLE_ID" in smp.columns else "PATIENT_ID"
        for _, r in smp.sort_values(sort_col, kind="stable").iterrows():
            if r["PATIENT_ID"] in sample_by_patient:
                multi += 1
            else:
                sample_by_patient[r["PATIENT_ID"]] = r.to_dict()
    seen: set[str] = set()
    for i, r in enumerate(pat.to_dict(orient="records"), start=1):
        pid = _clean(r.get("PATIENT_ID"))

        def reject(code: str, field: str) -> None:
            rejections.append({"row": i, "code": code, "field": field})

        if pid is None:
            reject("MISSING_REQUIRED", "PATIENT_ID")
            continue
        if pid in seen:
            reject("DUPLICATE_PATIENT", "PATIENT_ID")
            continue
        seen.add(pid)
        out: Dict[str, Any] = {"patient_id": pid, "source": spec.name}
        bad = False
        age, ok = _num(_clean(r.get(spec.patient_attrs["age"])))
        if not ok:
            reject("BAD_TYPE", "age")
            bad = True
        elif age is None:
            reject("MISSING_REQUIRED", "age")
            bad = True
        elif not spec.age_range[0] <= age <= spec.age_range[1]:
            reject("OUT_OF_RANGE", "age")
            bad = True
        out["age_years"] = age
        osm, ok = _num(_clean(r.get(spec.patient_attrs["os_months"])))
        if not ok:
            reject("BAD_TYPE", "os_months")
            bad = True
        elif osm is None:
            reject("MISSING_REQUIRED", "os_months")
            bad = True
        elif osm < 0:
            reject("OUT_OF_RANGE", "os_months")
            bad = True
        out["os_months"] = osm
        ev = _event(_clean(r.get(spec.patient_attrs["os_status"])))
        if ev is None:
            reject(
                "MISSING_REQUIRED"
                if _clean(r.get(spec.patient_attrs["os_status"])) is None
                else "BAD_ENUM",
                "os_status",
            )
            bad = True
        out["os_event"] = ev
        rm, ok = _num(_clean(r.get(spec.relapse_months))) if spec.relapse_months else (None, True)
        if not ok or (rm is not None and rm < 0):
            reject("BAD_TYPE" if not ok else "OUT_OF_RANGE", "relapse_months")
            bad = True
        rs_raw = _clean(r.get(spec.relapse_status)) if spec.relapse_status else None
        rs = _event(rs_raw)
        if rs_raw is not None and rs is None:
            reject("BAD_ENUM", "relapse_status")
            bad = True
        out["relapse_months"], out["relapse_event"] = rm, rs
        out["sex"] = (_clean(r.get(spec.patient_attrs.get("sex", ""))) or "").upper() or None
        out["subtype"] = _clean(r.get(spec.patient_attrs["subtype"]))
        out["menopausal_state"] = (
            _clean(r.get(spec.patient_attrs["menopausal_state"]))
            if "menopausal_state" in spec.patient_attrs
            else None
        )
        npi, ok = (
            _num(_clean(r.get(spec.patient_attrs["npi"])))
            if "npi" in spec.patient_attrs
            else (None, True)
        )
        out["npi"] = npi if ok else None
        srow = sample_by_patient.get(pid)
        merged = {**{k: r.get(v) for k, v in spec.patient_attrs.items() if k == "stage"}}
        if spec.sample_attrs and smp is not None and srow is None:
            reject("NO_SAMPLE_ROW", "sample")
            bad = True
        for field, attr in spec.sample_attrs.items():
            merged[field] = (srow or {}).get(attr) if srow else None
        for field in ("er", "pr", "her2"):
            v = _clean(merged.get(field))
            out[field] = v.upper() if v and v.upper() in ("POSITIVE", "NEGATIVE") else None
        stage_raw = _clean(merged.get("stage"))
        out["stage"] = spec.stage_map(stage_raw) if stage_raw else None
        out["grade"] = _clean(merged.get("grade"))
        if not bad:
            rows.append(out)
    codes: Dict[str, int] = {}
    for rj in rejections:
        codes[rj["code"]] = codes.get(rj["code"], 0) + 1
    rejected_rows = len({rj["row"] for rj in rejections})
    df = pd.DataFrame(rows)
    report = {
        "study": spec.name,
        "patients_in_file": int(len(pat)),
        "patients_loaded": int(len(df)),
        "rows_rejected": rejected_rows,
        "rejection_codes": dict(sorted(codes.items())),
        "rejections_by_code_and_field": {
            f"{c}:{f}": n
            for (c, f), n in sorted(
                {
                    (k, f): sum(1 for r in rejections if r["code"] == k and r["field"] == f)
                    for k in codes
                    for f in {r["field"] for r in rejections if r["code"] == k}
                }.items()
            )
        },
        "rejections": rejections,
        "patients_with_more_than_one_sample_row": multi,
    }
    return df, report
