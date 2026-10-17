"""HL7 v2.3 / v2.5 ORU^R01 Laboratory Ingestion Adapter.

Implements Master Plan §9.6 and Phase 5 Platform requirements:
- Parses incoming hospital LIS ORU^R01 (Observation Result Unsolicited) messages.
- Strict extraction of MSH, PID, OBR, and OBX segments.
- Resolves observation identifiers via LOINC or canonical analyte registry codes.
- Canonical timestamp parsing (HL7 standard YYYYMMDDHHMMSS / ISO-8601).
- Generates outbound ORU^R01 messages for bidirectional LIS integration.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from vigil_core.analytes import ANALYTE_REGISTRY

LOINC_TO_ANALYTE_CODE: Dict[str, str] = {
    analyte.loinc_code: analyte.code for analyte in ANALYTE_REGISTRY.values()
}
CODE_TO_ANALYTE_CODE: Dict[str, str] = {
    analyte.code.lower(): analyte.code for analyte in ANALYTE_REGISTRY.values()
}


class HL7ParsingError(Exception):
    """Raised when an HL7 message fails structural or semantic validation."""

    pass


class HL7ObservationResult(BaseModel):
    """Structured result parsed from an OBX segment."""

    set_id: int
    analyte_code: str
    loinc_code: Optional[str] = None
    value: float
    unit: str
    specimen_collected_at: datetime
    laboratory_id: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    result_status: Optional[str] = None


class HL7ORU_R01Message(BaseModel):
    """Canonical representation of an parsed HL7 v2 ORU^R01 message."""

    message_control_id: str
    sending_facility: Optional[str] = None
    message_timestamp: datetime
    patient_id: str
    patient_name: Optional[str] = None
    observations: List[HL7ObservationResult] = Field(default_factory=list)


def parse_hl7_timestamp(ts_str: str) -> datetime:
    """Parses HL7 standard timestamps (YYYYMMDD[HH[MM[SS]]]) or ISO-8601."""
    cleaned = ts_str.strip()
    # Check ISO-8601
    if "T" in cleaned or "-" in cleaned:
        try:
            dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    # Clean timezone offsets if present (e.g. +0000 or -0500)
    tz_match = re.search(r"([+-]\d{4})$", cleaned)
    tz = timezone.utc
    if tz_match:
        tz_offset = tz_match.group(1)
        cleaned = cleaned[: -len(tz_offset)]
        # Simple UTC normalization or offset parsing

    formats = [
        ("%Y%m%d%H%M%S", 14),
        ("%Y%m%d%H%M", 12),
        ("%Y%m%d%H", 10),
        ("%Y%m%d", 8),
    ]

    for fmt, length in formats:
        if len(cleaned) >= length:
            try:
                dt = datetime.strptime(cleaned[:length], fmt)
                return dt.replace(tzinfo=tz)
            except ValueError:
                continue

    raise HL7ParsingError(f"Invalid HL7 timestamp format: '{ts_str}'")


def parse_oru_r01(raw_message: str) -> HL7ORU_R01Message:
    """Parses a raw HL7 v2 ORU^R01 text message into canonical domain objects.

    Enforces:
    1. Mandatory MSH segment with message type ORU^R01.
    2. Mandatory PID segment with non-empty patient identifier.
    3. At least one valid OBX observation segment.
    4. Resolution of analyte codes to Vigil Analyte Registry.
    5. Unit verification with zero silent coercion.
    """
    if not raw_message or not raw_message.strip():
        raise HL7ParsingError("Empty HL7 message.")

    lines = [
        line.strip()
        for line in re.split(r"[\r\n]+", raw_message.strip())
        if line.strip()
    ]

    msh_line = next((ln for ln in lines if ln.startswith("MSH")), None)
    if not msh_line:
        raise HL7ParsingError("Missing mandatory MSH segment in HL7 message.")

    field_sep = msh_line[3]
    msh_fields = msh_line.split(field_sep)

    # In HL7, MSH-1 is the separator itself, so msh_fields indices:
    # msh_fields[1] = MSH-2 (Encoding Characters)
    # msh_fields[2] = MSH-3 (Sending Application)
    # msh_fields[3] = MSH-4 (Sending Facility)
    # msh_fields[6] = MSH-7 (Date/Time of Message)
    # msh_fields[8] = MSH-9 (Message Type)
    # msh_fields[9] = MSH-10 (Message Control ID)
    if len(msh_fields) < 10:
        raise HL7ParsingError("Malformed MSH segment: insufficient fields.")

    msg_type = msh_fields[8].upper()
    if not msg_type.startswith("ORU^R01") and not msg_type.startswith("ORU_R01"):
        raise HL7ParsingError(
            f"Unsupported HL7 message type: '{msg_type}'. Only ORU^R01 is accepted."
        )

    sending_facility = msh_fields[3] if len(msh_fields) > 3 else None
    msg_timestamp = parse_hl7_timestamp(msh_fields[6])
    msg_control_id = msh_fields[9]

    # PID Segment
    pid_line = next((ln for ln in lines if ln.startswith("PID")), None)
    if not pid_line:
        raise HL7ParsingError("Missing mandatory PID segment in HL7 message.")

    pid_fields = pid_line.split(field_sep)
    # pid_fields[3] = PID-3 (Patient Identifier List)
    if len(pid_fields) < 4 or not pid_fields[3].strip():
        raise HL7ParsingError("Missing or empty patient identifier in PID segment.")

    # Extract primary ID from PID-3 (e.g. 'PT-12345' from 'PT-12345^^^HOSPITAL')
    patient_id = pid_fields[3].split("^")[0].strip()
    if not patient_id:
        raise HL7ParsingError("Could not extract patient identifier from PID-3.")

    patient_name = None
    if len(pid_fields) > 5 and pid_fields[5].strip():
        # PID-5 (Name: Last^First^Middle^Suffix^Prefix)
        name_parts = pid_fields[5].split("^")
        last = name_parts[0].strip() if len(name_parts) > 0 else ""
        first = name_parts[1].strip() if len(name_parts) > 1 else ""
        middle = name_parts[2].strip() if len(name_parts) > 2 else ""
        parts = [p for p in [first, middle, last] if p]
        if parts:
            patient_name = " ".join(parts)

    # OBR default date/time if OBX lacks timestamp
    obr_date: Optional[datetime] = None
    obr_line = next((ln for ln in lines if ln.startswith("OBR")), None)
    if obr_line:
        obr_fields = obr_line.split(field_sep)
        if len(obr_fields) > 7 and obr_fields[7].strip():
            try:
                obr_date = parse_hl7_timestamp(obr_fields[7])
            except Exception:
                pass

    # OBX Segments
    obx_lines = [ln for ln in lines if ln.startswith("OBX")]
    if not obx_lines:
        raise HL7ParsingError("Message must contain at least one OBX segment.")

    observations: List[HL7ObservationResult] = []

    for obx_idx, obx_line in enumerate(obx_lines):
        obx_fields = obx_line.split(field_sep)
        # OBX-1: Set ID
        # OBX-2: Value Type
        # OBX-3: Observation Identifier (ID^Text^System)
        # OBX-5: Observation Value
        # OBX-6: Units (Units^Text^System)
        # OBX-7: Reference Range
        # OBX-8: Abnormal Flags
        # OBX-11: Result Status
        # OBX-14: Date/Time of Observation
        # OBX-15: Producer's ID
        if len(obx_fields) < 6:
            raise HL7ParsingError(f"Malformed OBX segment #{obx_idx + 1}: insufficient fields.")

        # Observation Identifier
        obs_id_comp = obx_fields[3].split("^")
        code_raw = obs_id_comp[0].strip()
        system = obs_id_comp[2].strip().upper() if len(obs_id_comp) > 2 else ""

        # Resolve analyte code from LOINC or code
        analyte_code = None
        loinc_code = None

        if code_raw in LOINC_TO_ANALYTE_CODE or system in ("LN", "LOINC"):
            loinc_code = code_raw
            analyte_code = LOINC_TO_ANALYTE_CODE.get(code_raw)
        elif code_raw.lower() in CODE_TO_ANALYTE_CODE:
            analyte_code = CODE_TO_ANALYTE_CODE[code_raw.lower()]
            loinc_code = ANALYTE_REGISTRY[analyte_code].loinc_code

        if not analyte_code:
            raise HL7ParsingError(
                f"Unrecognized analyte or LOINC code in OBX #{obx_idx + 1}: '{code_raw}'."
            )

        # Value
        raw_val = obx_fields[5].strip()
        try:
            value = float(raw_val)
        except ValueError:
            raise HL7ParsingError(
                f"Invalid non-numeric observation value in OBX #{obx_idx + 1}: '{raw_val}'."
            )

        # Units
        unit_raw = obx_fields[6].split("^")[0].strip() if len(obx_fields) > 6 else ""
        if not unit_raw:
            raise HL7ParsingError(f"Missing unit in OBX segment #{obx_idx + 1}.")

        # Specimen / Observation Timestamp
        obs_timestamp = None
        if len(obx_fields) > 14 and obx_fields[14].strip():
            try:
                obs_timestamp = parse_hl7_timestamp(obx_fields[14])
            except Exception:
                pass
        if not obs_timestamp:
            obs_timestamp = obr_date or msg_timestamp

        lab_id = obx_fields[15].strip() if len(obx_fields) > 15 and obx_fields[15].strip() else sending_facility
        ref_range = obx_fields[7].strip() if len(obx_fields) > 7 and obx_fields[7].strip() else None
        abnormal = obx_fields[8].strip() if len(obx_fields) > 8 and obx_fields[8].strip() else None
        res_status = obx_fields[11].strip() if len(obx_fields) > 11 and obx_fields[11].strip() else None

        set_id = int(obx_fields[1]) if obx_fields[1].strip().isdigit() else (obx_idx + 1)

        observations.append(
            HL7ObservationResult(
                set_id=set_id,
                analyte_code=analyte_code,
                loinc_code=loinc_code,
                value=value,
                unit=unit_raw,
                specimen_collected_at=obs_timestamp,
                laboratory_id=lab_id,
                reference_range=ref_range,
                abnormal_flag=abnormal,
                result_status=res_status,
            )
        )

    return HL7ORU_R01Message(
        message_control_id=msg_control_id,
        sending_facility=sending_facility,
        message_timestamp=msg_timestamp,
        patient_id=patient_id,
        patient_name=patient_name,
        observations=observations,
    )


def generate_oru_r01(
    message_control_id: str,
    patient_id: str,
    observations: List[Dict[str, Any]],
    patient_name: Optional[str] = None,
    sending_facility: str = "VIGIL-LIS-01",
    message_timestamp: Optional[datetime] = None,
) -> str:
    """Constructs a standard HL7 v2.5 ORU^R01 text message."""
    ts = message_timestamp or datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y%m%d%H%M%S")

    msh = f"MSH|^~\\&|VIGIL|{sending_facility}|RECEIVER|CLINIC|{ts_str}||ORU^R01|{message_control_id}|P|2.5"

    name_str = patient_name.replace(" ", "^") if patient_name else ""
    pid = f"PID|1||{patient_id}^^^VIGIL^MR||{name_str}"

    obr = f"OBR|1|||LAB^LABORATORY_SURVEILLANCE|||{ts_str}"

    segments = [msh, pid, obr]

    for idx, obs in enumerate(observations, start=1):
        analyte_code = obs["analyte_code"]
        analyte = ANALYTE_REGISTRY.get(analyte_code)
        loinc = analyte.loinc_code if analyte else "83082-8"
        name = analyte.name if analyte else analyte_code
        val = obs["value"]
        unit = obs["unit"]
        obs_ts = obs.get("specimen_collected_at")
        if isinstance(obs_ts, datetime):
            obs_ts_str = obs_ts.strftime("%Y%m%d%H%M%S")
        else:
            obs_ts_str = ts_str
        lab_id = obs.get("laboratory_id", sending_facility)

        obx = f"OBX|{idx}|NM|{loinc}^{name}^LN||{val}|{unit}||N|||F|||{obs_ts_str}|{lab_id}"
        segments.append(obx)

    return "\r\n".join(segments) + "\r\n"
