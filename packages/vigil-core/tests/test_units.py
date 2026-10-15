"""
Tests for vigil_core.units: Unit conversions, dimensional validation, and property tests.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from vigil_core.units import (
    IncompatibleUnitsError,
    InvalidUnitError,
    UnitDimension,
    convert_units,
    get_unit_dimension,
    normalize_unit_string,
)


def test_normalize_unit_string():
    assert normalize_unit_string("mg/dL") == "mg/dL"
    assert normalize_unit_string(" g / dL ") == "g/dL"
    assert normalize_unit_string("µmol/L") == "umol/L"
    assert normalize_unit_string("U/L") == "U/L"

    with pytest.raises(InvalidUnitError):
        normalize_unit_string("apples_and_oranges")


def test_get_unit_dimension():
    assert get_unit_dimension("mg/dL") == UnitDimension.MASS_CONCENTRATION
    assert get_unit_dimension("umol/L") == UnitDimension.MOLAR_CONCENTRATION
    assert get_unit_dimension("U/L") == UnitDimension.ENZYMATIC_ACTIVITY
    assert get_unit_dimension("10*9/L") == UnitDimension.CELL_COUNT
    assert get_unit_dimension("%") == UnitDimension.PERCENTAGE
    assert get_unit_dimension("mm/h") == UnitDimension.VELOCITY


def test_mass_concentration_conversions():
    # 1 g/dL = 10 g/L = 1000 mg/dL = 10000 mg/L
    assert convert_units(1.0, "g/dL", "g/L") == pytest.approx(10.0)
    assert convert_units(10.0, "g/L", "g/dL") == pytest.approx(1.0)
    assert convert_units(100.0, "mg/dL", "g/L") == pytest.approx(1.0)
    assert convert_units(1.0, "ug/L", "ng/mL") == pytest.approx(1.0)


def test_enzymatic_activity_conversions():
    # 60 U/L = 1.0 ukat/L
    assert convert_units(60.0, "U/L", "ukat/L") == pytest.approx(1.0)
    assert convert_units(1.0, "ukat/L", "U/L") == pytest.approx(60.0)
    # [iU]/mL to U/L (1 U/mL = 1000 U/L)
    assert convert_units(30.0, "[iU]/mL", "U/L") == pytest.approx(30000.0)


def test_cell_count_conversions():
    # 1.0 x 10*9/L = 1000 /uL = 1.0 x 10*3/uL
    assert convert_units(4.5, "10*9/L", "/uL") == pytest.approx(4500.0)
    assert convert_units(4500.0, "/uL", "10*9/L") == pytest.approx(4.5)


def test_molecular_weight_conversions():
    # Creatinine: MW = 113.12 g/mol
    # 1.0 mg/dL = 0.01 g/L = (0.01 / 113.12) mol/L = 8.84017e-5 mol/L = 88.4017 umol/L
    umol = convert_units(1.0, "mg/dL", "umol/L", analyte_code="creatinine")
    assert umol == pytest.approx(88.4017, rel=1e-3)

    mg_dl = convert_units(umol, "umol/L", "mg/dL", analyte_code="creatinine")
    assert mg_dl == pytest.approx(1.0, rel=1e-3)

    # Total Bilirubin: MW = 584.66 g/mol
    # 1.0 mg/dL = 17.104 umol/L
    bili_umol = convert_units(1.0, "mg/dL", "umol/L", analyte_code="total_bilirubin")
    assert bili_umol == pytest.approx(17.104, rel=1e-3)


def test_incompatible_conversions_raise_explicit_error():
    # Mass to Activity
    with pytest.raises(IncompatibleUnitsError):
        convert_units(10.0, "mg/dL", "U/L")

    # Cell count to Mass
    with pytest.raises(IncompatibleUnitsError):
        convert_units(5.0, "10*9/L", "mg/dL")

    # Mass to Molar without analyte code
    with pytest.raises(IncompatibleUnitsError):
        convert_units(1.0, "mg/dL", "umol/L")

    # Unknown analyte code for MW conversion
    with pytest.raises(IncompatibleUnitsError):
        convert_units(1.0, "mg/dL", "umol/L", analyte_code="unknown_synthetic_analyte")


@given(
    val=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
)
def test_hypothesis_round_trip_mass(val: float):
    converted = convert_units(val, "mg/dL", "g/L")
    round_trip = convert_units(converted, "g/L", "mg/dL")
    assert round_trip == pytest.approx(val, rel=1e-5)


@given(
    val=st.floats(min_value=0.1, max_value=500.0, allow_nan=False, allow_infinity=False),
)
def test_hypothesis_round_trip_creatinine_mw(val: float):
    converted = convert_units(val, "mg/dL", "umol/L", analyte_code="creatinine")
    round_trip = convert_units(converted, "umol/L", "mg/dL", analyte_code="creatinine")
    assert round_trip == pytest.approx(val, rel=1e-4)
