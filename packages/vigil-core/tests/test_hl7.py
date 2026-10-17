"""Unit tests for vigil_core.hl7: HL7 v2 ORU^R01 parser and generator."""

import pytest
from vigil_core.hl7 import (
    HL7ParsingError,
    generate_oru_r01,
    parse_hl7_timestamp,
    parse_oru_r01,
)


def test_parse_hl7_timestamp():
    dt = parse_hl7_timestamp("20261017083000")
    assert dt.year == 2026 and dt.month == 10 and dt.day == 17
    assert dt.hour == 8 and dt.minute == 30 and dt.second == 0

    # ISO-8601 fallback
    dt_iso = parse_hl7_timestamp("2026-10-17T08:30:00+00:00")
    assert dt_iso.year == 2026 and dt_iso.hour == 8

    with pytest.raises(HL7ParsingError):
        parse_hl7_timestamp("not-a-date")


def test_parse_valid_oru_r01_loinc():
    raw_hl7 = (
        "MSH|^~\\&|LAB_SYS|HOSP_A|VIGIL|ONCOLOGY|20261017083000||ORU^R01|MSG-00123|P|2.5\r\n"
        "PID|1||PAT-98765^^^HOSP_A^MR||Doe^Jane^^^Ms.\r\n"
        "OBR|1|||LAB^ROUTINE_ONCOLOGY|||20261017081500\r\n"
        "OBX|1|NM|83082-8^CA 15-3^LN||24.5|U/mL|< 30.0|N|||F|||20261017081500|LAB-01\r\n"
        "OBX|2|NM|1742-6^ALT^LN||28.0|U/L|7-35|N|||F|||20261017081500|LAB-01\r\n"
    )
    msg = parse_oru_r01(raw_hl7)
    assert msg.message_control_id == "MSG-00123"
    assert msg.patient_id == "PAT-98765"
    assert msg.patient_name == "Jane Doe"
    assert len(msg.observations) == 2

    obs1 = msg.observations[0]
    assert obs1.analyte_code == "ca_15_3"
    assert obs1.loinc_code == "83082-8"
    assert obs1.value == 24.5
    assert obs1.unit == "U/mL"
    assert obs1.laboratory_id == "LAB-01"

    obs2 = msg.observations[1]
    assert obs2.analyte_code == "alt"
    assert obs2.value == 28.0
    assert obs2.unit == "U/L"


def test_parse_valid_oru_r01_analyte_code():
    raw_hl7 = (
        "MSH|^~\\&|LIS|FACILITY|VIGIL|CLINIC|20261017083000||ORU^R01|MSG-999|P|2.5\r\n"
        "PID|1||PT-12345||Smith^John\r\n"
        "OBR|1|||SURVEILLANCE|||20261017080000\r\n"
        "OBX|1|NM|ca_15_3^CA 15-3^LOCAL||32.4|U/mL|< 30.0|H|||F|||20261017080000|FACILITY\r\n"
    )
    msg = parse_oru_r01(raw_hl7)
    assert msg.patient_id == "PT-12345"
    assert len(msg.observations) == 1
    assert msg.observations[0].analyte_code == "ca_15_3"
    assert msg.observations[0].value == 32.4


def test_parse_malformed_messages():
    # Empty
    with pytest.raises(HL7ParsingError, match="Empty"):
        parse_oru_r01("")

    # Missing MSH
    with pytest.raises(HL7ParsingError, match="Missing mandatory MSH"):
        parse_oru_r01("PID|1||PT-001\r\nOBX|1|NM|83082-8||25|U/mL\r\n")

    # Wrong message type
    bad_type = "MSH|^~\\&|A|B|C|D|20261017||ADT^A01|001|P|2.5\r\nPID|1||PT-001\r\nOBX|1|NM|83082-8||25|U/mL\r\n"
    with pytest.raises(HL7ParsingError, match="Unsupported HL7 message type"):
        parse_oru_r01(bad_type)

    # Missing PID
    no_pid = "MSH|^~\\&|A|B|C|D|20261017||ORU^R01|001|P|2.5\r\nOBX|1|NM|83082-8||25|U/mL\r\n"
    with pytest.raises(HL7ParsingError, match="Missing mandatory PID"):
        parse_oru_r01(no_pid)

    # Empty patient id in PID
    empty_pid = "MSH|^~\\&|A|B|C|D|20261017||ORU^R01|001|P|2.5\r\nPID|1||   \r\nOBX|1|NM|83082-8||25|U/mL\r\n"
    with pytest.raises(HL7ParsingError, match="Missing or empty patient identifier"):
        parse_oru_r01(empty_pid)

    # Missing OBX
    no_obx = "MSH|^~\\&|A|B|C|D|20261017||ORU^R01|001|P|2.5\r\nPID|1||PT-001\r\n"
    with pytest.raises(HL7ParsingError, match="at least one OBX"):
        parse_oru_r01(no_obx)

    # Unrecognized LOINC / analyte
    bad_analyte = (
        "MSH|^~\\&|A|B|C|D|20261017||ORU^R01|001|P|2.5\r\n"
        "PID|1||PT-001\r\n"
        "OBX|1|NM|99999-9^Unknown^LN||25|U/mL\r\n"
    )
    with pytest.raises(HL7ParsingError, match="Unrecognized analyte"):
        parse_oru_r01(bad_analyte)

    # Non-numeric value
    bad_val = (
        "MSH|^~\\&|A|B|C|D|20261017||ORU^R01|001|P|2.5\r\n"
        "PID|1||PT-001\r\n"
        "OBX|1|NM|83082-8^CA 15-3^LN||NON_NUMERIC|U/mL\r\n"
    )
    with pytest.raises(HL7ParsingError, match="Invalid non-numeric"):
        parse_oru_r01(bad_val)


def test_round_trip_generation_and_parsing():
    obs_list = [
        {"analyte_code": "ca_15_3", "value": 22.1, "unit": "U/mL"},
        {"analyte_code": "alt", "value": 31.0, "unit": "U/L"},
    ]
    raw = generate_oru_r01(
        message_control_id="CTRL-42",
        patient_id="PT-ROUNDTRIP",
        observations=obs_list,
        patient_name="Alice Smith",
        sending_facility="FAC-001",
    )
    parsed = parse_oru_r01(raw)
    assert parsed.message_control_id == "CTRL-42"
    assert parsed.patient_id == "PT-ROUNDTRIP"
    assert len(parsed.observations) == 2
    assert parsed.observations[0].analyte_code == "ca_15_3"
    assert parsed.observations[0].value == 22.1
    assert parsed.observations[1].analyte_code == "alt"
    assert parsed.observations[1].value == 31.0
