"""Parser and synthetic-report tests. No Tesseract required."""

from __future__ import annotations

from vigil_api.ocr import (
    extract_from_bytes,
    parse_lab_text,
    render_synthetic_report,
    suggestion_triple,
)


def test_parser_reads_ca15_3_line_and_does_not_take_the_15_from_the_name():
    text = (
        "Vigil Synthetic Laboratory\n"
        "Patient: SYNTHETIC-NOT-A-PERSON\n"
        "Collected: 2026-03-15\n"
        "CA 15-3    24.6 U/mL\n"
    )
    parsed = parse_lab_text(text)
    assert parsed.analyte_code == "ca_15_3"
    assert parsed.value == 24.6
    assert parsed.unit in ("U/mL", "[iU]/mL")
    assert parsed.specimen_collected_at == "2026-03-15"


def test_parser_reads_cea():
    parsed = parse_lab_text("CEA    8.0 ng/mL\nCollected: 2026-01-02")
    assert parsed.analyte_code == "cea"
    assert parsed.value == 8.0
    assert parsed.unit == "ng/mL"


def test_parser_flags_comma_decimal_and_empty_text():
    parsed = parse_lab_text("CA 15-3    24,6 U/mL")
    assert parsed.value == 24.6
    assert any(f.reason == "comma_decimal" for f in parsed.flags)
    empty = parse_lab_text("   ")
    assert empty.analyte_code is None
    assert empty.value is None


def test_pdf_text_layer_round_trip_without_tesseract():
    report = render_synthetic_report(
        analyte_code="ca_15_3", value=31.4, unit="U/mL", collected_on="2026-04-01"
    )
    extracted = extract_from_bytes(report.pdf_bytes, "application/pdf")
    assert extracted.engine == "pdf_text"
    triple = suggestion_triple(extracted.suggestion)
    assert triple == ("ca_15_3", 31.4, "U/mL")
