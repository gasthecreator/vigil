"""On-site HL7 v2 ORU^R01 -> ``lab_observations`` rows (run inside the hospital, never remotely).

HL7 results carry absolute timestamps and the hospital's own patient identifier. The extraction format forbids both,
so this converter runs where the identifiers live, with two inputs that never leave the site: a map from the local
patient identifier to the diagnosis date, and a secret used to derive the pseudonym. Only the converted rows
(pseudonym + relative day) are exported; they then pass through ``ingest`` like any other file.

Each OBX segment is converted on its own, so one bad result rejects that result and not the message. Rejection
reasons are fixed codes; free text from the message (which may contain a name) is never copied into a report.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from datetime import date
from typing import Any, Callable, Dict, Iterable, List, Mapping, Tuple

from vigil_core.analytes import ANALYTE_REGISTRY
from vigil_core.hl7 import HL7ParsingError, parse_oru_r01


def hmac_pseudonym(secret: bytes) -> Callable[[str], str]:
    """Deterministic pseudonym ``VIGIL-<12 hex>`` from a locally held secret. The secret is supplied at run time."""
    if not secret or len(secret) < 16:
        raise ValueError("pseudonym secret must be at least 16 bytes and supplied at run time")

    def derive(local_id: str) -> str:
        return (
            "VIGIL-" + hmac.new(secret, local_id.encode("utf-8"), hashlib.sha256).hexdigest()[:12]
        )

    return derive


def _classify(exc: HL7ParsingError) -> str:
    msg = str(exc)
    for needle, code in (
        ("Unrecognized analyte", "UNKNOWN_ANALYTE"),
        ("non-numeric", "NON_NUMERIC_VALUE"),
        ("Missing unit", "MISSING_UNIT"),
        ("Malformed OBX", "MALFORMED_OBX"),
        ("OBX", "NO_OBX"),
        ("MSH", "NO_MSH"),
        ("PID", "NO_PID"),
        ("patient identifier", "NO_PID"),
        ("Empty", "EMPTY_MESSAGE"),
    ):
        if needle in msg:
            return code
    return "HL7_PARSE_ERROR"


def convert_messages(
    messages: Iterable[str],
    index_dates: Mapping[str, date],
    pseudonym: Callable[[str], str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return ``(lab_rows, rejections)``. ``rejections`` entries carry message number, OBX number and a fixed code."""
    rows: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for m_no, msg in enumerate(messages, start=1):
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", (msg or "").strip()) if ln.strip()]
        head = [ln for ln in lines if not ln.startswith("OBX")]
        obx = [ln for ln in lines if ln.startswith("OBX")]
        if not obx:
            rejected.append({"message": m_no, "obx": 0, "code": "NO_OBX"})
            continue
        for o_no, line in enumerate(obx, start=1):
            try:
                parsed = parse_oru_r01("\r".join(head + [line]))
            except HL7ParsingError as exc:
                rejected.append({"message": m_no, "obx": o_no, "code": _classify(exc)})
                continue
            local = parsed.patient_id
            if local not in index_dates:
                rejected.append({"message": m_no, "obx": o_no, "code": "NO_INDEX_DATE"})
                continue
            for ob in parsed.observations:
                day = (ob.specimen_collected_at.date() - index_dates[local]).days
                if day < 0:
                    rejected.append({"message": m_no, "obx": o_no, "code": "BEFORE_DIAGNOSIS"})
                    continue
                a = ANALYTE_REGISTRY[ob.analyte_code]
                rows.append(
                    {
                        "patient_id": pseudonym(local),
                        "observation_day": day,
                        "analyte_code": a.loinc_code,
                        "analyte_name": a.code,
                        "value_numeric": ob.value,
                        "unit_ucum": ob.unit,
                        "ref_low": "",
                        "ref_high": "",
                    }
                )
    return rows, rejected
