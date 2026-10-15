"""
Tests for vigil_core.analytes: Analyte registry completeness, RCV mathematics, and plausibility boundary validation.
"""

import pytest

from vigil_core.analytes import (
    ANALYTE_REGISTRY,
    PlausibilityStatus,
    calculate_rcv,
    check_plausibility,
    get_analyte,
    list_analytes,
)


def test_analyte_registry_contains_at_least_20_analytes():
    analytes = list_analytes()
    assert len(analytes) >= 20, f"Expected >= 20 analytes, found {len(analytes)}"
    assert len(ANALYTE_REGISTRY) >= 20


def test_analyte_registry_specifications():
    required_codes = [
        "ca_15_3", "ca_27_29", "cea", "alt", "ast", "alp", "ggt",
        "total_bilirubin", "direct_bilirubin", "albumin", "total_protein",
        "ldh", "calcium", "corrected_calcium", "phosphate", "creatinine",
        "egfr", "urea", "haemoglobin", "platelets", "wbc", "anc", "nlr",
        "esr", "crp", "inr"
    ]
    for code in required_codes:
        analyte = get_analyte(code)
        assert analyte.code == code
        assert analyte.name is not None and len(analyte.name) > 0
        assert analyte.loinc_code is not None and len(analyte.loinc_code) > 0
        assert analyte.canonical_unit is not None
        assert analyte.biological_variation.cv_i > 0
        assert analyte.biological_variation.cv_g > 0
        assert analyte.biological_variation.index_of_individuality > 0
        assert analyte.analytical_spec.cv_a_desirable > 0
        assert analyte.plausibility.physiological_max > analyte.plausibility.physiological_min
        assert analyte.plausibility.reference_high > analyte.plausibility.reference_low


def test_rcv_calculation_matches_analytical_formula():
    # CA 15-3: CVi = 5.8%, desirable CVa = 2.9%
    # Normal 95% bidirectional: RCV = sqrt(2) * 1.96 * sqrt(2.9^2 + 5.8^2)
    # sqrt(2)*1.96 = 2.7718585...
    # sqrt(8.41 + 33.64) = sqrt(42.05) = 6.484597...
    # RCV = 2.7718585 * 6.484597 = 17.974%
    rcv_ca153 = calculate_rcv("ca_15_3", confidence=0.95, two_sided=True, log_normal=False)
    assert rcv_ca153 == pytest.approx(17.974, rel=1e-3)

    # 99% confidence bidirectional (Z = 2.576)
    rcv_ca153_99 = calculate_rcv("ca_15_3", confidence=0.99, two_sided=True, log_normal=False)
    assert rcv_ca153_99 > rcv_ca153
    expected_99 = math_sqrt_2 = 1.41421356 * 2.576 * 6.484597
    assert rcv_ca153_99 == pytest.approx(expected_99, rel=1e-3)

    # Log-normal RCV for skewed analytes
    rcv_ca153_log = calculate_rcv("ca_15_3", confidence=0.95, two_sided=True, log_normal=True)
    assert rcv_ca153_log > 0


def test_plausibility_validation_normal_value():
    res = check_plausibility("alt", 25.0, "U/L")
    assert res.is_valid is True
    assert res.is_critical is False
    assert res.status == PlausibilityStatus.VALID_NORMAL


def test_plausibility_validation_elevated_value():
    res = check_plausibility("ca_15_3", 45.0, "[iU]/mL")
    assert res.is_valid is True
    assert res.is_critical is False
    assert res.status == PlausibilityStatus.VALID_ELEVATED


def test_plausibility_validation_critical_high():
    # Calcium reference: 8.5 - 10.5, critical high: 13.0
    res = check_plausibility("calcium", 14.2, "mg/dL")
    assert res.is_valid is True
    assert res.is_critical is True
    assert res.status == PlausibilityStatus.CRITICAL_HIGH


def test_plausibility_validation_unphysiological():
    # ALT physiological max is 5000 U/L
    res = check_plausibility("alt", 99999.0, "U/L")
    assert res.is_valid is False
    assert res.is_critical is True
    assert res.status == PlausibilityStatus.UNPHYSIOLOGICAL_HIGH

    # Creatinine physiological min is 0.1 mg/dL
    res_low = check_plausibility("creatinine", 0.001, "mg/dL")
    assert res_low.is_valid is False
    assert res_low.status == PlausibilityStatus.UNPHYSIOLOGICAL_LOW


def test_plausibility_with_unit_conversion():
    # Creatinine: 1.0 mg/dL = 88.4 umol/L (normal range ~44 - 97 umol/L)
    res = check_plausibility("creatinine", 88.4, "umol/L")
    assert res.is_valid is True
    assert res.status == PlausibilityStatus.VALID_NORMAL
    assert res.canonical_unit == "mg/dL"
    assert res.canonical_value == pytest.approx(1.0, rel=1e-2)
