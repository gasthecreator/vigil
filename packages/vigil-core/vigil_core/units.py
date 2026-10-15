"""
vigil_core.units

Unit conversion library with strict dimensional verification and UCUM adherence.
Explicitly rejects incompatible unit conversions (never silent coercion).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Dict, Optional, Tuple


class UnitDimension(str, Enum):
    MASS_CONCENTRATION = "mass_concentration"  # Canonical: g/L
    MOLAR_CONCENTRATION = "molar_concentration"  # Canonical: mol/L
    ENZYMATIC_ACTIVITY = "enzymatic_activity"  # Canonical: U/L
    CELL_COUNT = "cell_count"  # Canonical: 10*9/L (/uL or /L)
    PERCENTAGE = "percentage"  # Canonical: %
    TIME = "time"  # Canonical: s or min
    RATIO = "ratio"  # Canonical: 1 (dimensionless)
    VELOCITY = "velocity"  # Canonical: mm/h (e.g., ESR)


class UnitConversionError(ValueError):
    """Base exception for unit conversion failures."""
    pass


class IncompatibleUnitsError(UnitConversionError):
    """Raised when attempting to convert between different non-convertible dimensions."""
    pass


class InvalidUnitError(UnitConversionError):
    """Raised when an unrecognized or malformed unit string is supplied."""
    pass


# Molecular weights (g/mol) for common analytes requiring mass <-> molar conversion
MOLECULAR_WEIGHTS: Dict[str, float] = {
    "creatinine": 113.12,
    "total_bilirubin": 584.66,
    "direct_bilirubin": 584.66,
    "calcium": 40.078,
    "corrected_calcium": 40.078,
    "phosphate": 94.97,  # inorganic phosphate as PO4
    "urea": 60.06,
    "glucose": 180.16,
    "uric_acid": 168.11,
}

# Unit specifications: mapping of unit string to (Dimension, Scale to Canonical Base)
# Canonical bases:
# - MASS_CONCENTRATION: g/L
# - MOLAR_CONCENTRATION: mol/L
# - ENZYMATIC_ACTIVITY: U/L
# - CELL_COUNT: 10*9/L
# - PERCENTAGE: %
# - RATIO: 1
# - VELOCITY: mm/h
UNIT_REGISTRY: Dict[str, Tuple[UnitDimension, float]] = {
    # Mass concentration (base: g/L)
    "g/L": (UnitDimension.MASS_CONCENTRATION, 1.0),
    "g/dL": (UnitDimension.MASS_CONCENTRATION, 10.0),
    "mg/dL": (UnitDimension.MASS_CONCENTRATION, 0.01),
    "mg/L": (UnitDimension.MASS_CONCENTRATION, 0.001),
    "ug/L": (UnitDimension.MASS_CONCENTRATION, 1e-6),
    "ug/mL": (UnitDimension.MASS_CONCENTRATION, 0.001),
    "ng/mL": (UnitDimension.MASS_CONCENTRATION, 1e-6),
    "pg/mL": (UnitDimension.MASS_CONCENTRATION, 1e-9),

    # Molar concentration (base: mol/L)
    "mol/L": (UnitDimension.MOLAR_CONCENTRATION, 1.0),
    "mmol/L": (UnitDimension.MOLAR_CONCENTRATION, 1e-3),
    "umol/L": (UnitDimension.MOLAR_CONCENTRATION, 1e-6),
    "nmol/L": (UnitDimension.MOLAR_CONCENTRATION, 1e-9),
    "pmol/L": (UnitDimension.MOLAR_CONCENTRATION, 1e-12),

    # Enzymatic activity / arbitrary units (base: U/L)
    "U/L": (UnitDimension.ENZYMATIC_ACTIVITY, 1.0),
    "IU/L": (UnitDimension.ENZYMATIC_ACTIVITY, 1.0),
    "[iU]/L": (UnitDimension.ENZYMATIC_ACTIVITY, 1.0),
    "U/mL": (UnitDimension.ENZYMATIC_ACTIVITY, 1000.0),
    "kU/L": (UnitDimension.ENZYMATIC_ACTIVITY, 1000.0),
    "ukat/L": (UnitDimension.ENZYMATIC_ACTIVITY, 60.0),  # 1 ukat/L = 60 U/L
    "[iU]/mL": (UnitDimension.ENZYMATIC_ACTIVITY, 1000.0),  # CA 15-3 standard unit

    # Cell count (base: 10*9/L, equivalent to 10^3/uL or x10^9/L)
    "10*9/L": (UnitDimension.CELL_COUNT, 1.0),
    "10^9/L": (UnitDimension.CELL_COUNT, 1.0),
    "x10^9/L": (UnitDimension.CELL_COUNT, 1.0),
    "10*3/uL": (UnitDimension.CELL_COUNT, 1.0),
    "10^3/uL": (UnitDimension.CELL_COUNT, 1.0),
    "/uL": (UnitDimension.CELL_COUNT, 1e-3),
    "/mcL": (UnitDimension.CELL_COUNT, 1e-3),
    "/mm3": (UnitDimension.CELL_COUNT, 1e-3),
    "cells/uL": (UnitDimension.CELL_COUNT, 1e-3),
    "10*12/L": (UnitDimension.CELL_COUNT, 1000.0),  # RBC count
    "10^12/L": (UnitDimension.CELL_COUNT, 1000.0),

    # Percentage
    "%": (UnitDimension.PERCENTAGE, 1.0),

    # Velocity
    "mm/h": (UnitDimension.VELOCITY, 1.0),
    "mm/hr": (UnitDimension.VELOCITY, 1.0),

    # Ratio / dimensionless
    "1": (UnitDimension.RATIO, 1.0),
    "ratio": (UnitDimension.RATIO, 1.0),
    "": (UnitDimension.RATIO, 1.0),
}


def normalize_unit_string(unit_str: str) -> str:
    """Normalizes raw unit strings to canonical registry keys."""
    if unit_str is None:
        raise InvalidUnitError("Unit string cannot be None")
    s = unit_str.strip()
    # Normalize common variations
    s_clean = s.replace("µ", "u").replace("μ", "u").replace("·", "/").replace(" ", "")
    if s_clean in UNIT_REGISTRY:
        return s_clean
    # Case-insensitive search
    for k in UNIT_REGISTRY:
        if k.lower() == s_clean.lower():
            return k
    raise InvalidUnitError(f"Unrecognized unit string: '{unit_str}'")


def get_unit_dimension(unit_str: str) -> UnitDimension:
    """Returns the physical dimension of the specified unit."""
    key = normalize_unit_string(unit_str)
    return UNIT_REGISTRY[key][0]


def convert_units(
    value: float,
    from_unit: str,
    to_unit: str,
    analyte_code: Optional[str] = None,
) -> float:
    """
    Converts a numerical laboratory value from one unit to another.

    Parameters:
        value: Numerical value to convert.
        from_unit: Source unit string (UCUM or accepted alias).
        to_unit: Target unit string (UCUM or accepted alias).
        analyte_code: Optional analyte identifier (e.g. 'creatinine', 'calcium')
                      required when bridging mass and molar dimensions.

    Returns:
        Converted value in target units.

    Raises:
        InvalidUnitError: If either unit is unrecognized.
        IncompatibleUnitsError: If units belong to incompatible dimensions or lack MW bridge.
    """
    if math.isnan(value) or math.isinf(value):
        return value

    norm_from = normalize_unit_string(from_unit)
    norm_to = normalize_unit_string(to_unit)

    if norm_from == norm_to:
        return float(value)

    dim_from, scale_from = UNIT_REGISTRY[norm_from]
    dim_to, scale_to = UNIT_REGISTRY[norm_to]

    # Case 1: Same physical dimension (linear scaling via canonical base)
    if dim_from == dim_to:
        base_value = value * scale_from
        return base_value / scale_to

    # Case 2: Mass concentration <-> Molar concentration bridge
    if (dim_from == UnitDimension.MASS_CONCENTRATION and dim_to == UnitDimension.MOLAR_CONCENTRATION) or \
       (dim_from == UnitDimension.MOLAR_CONCENTRATION and dim_to == UnitDimension.MASS_CONCENTRATION):
        if not analyte_code:
            raise IncompatibleUnitsError(
                f"Cannot convert between '{from_unit}' ({dim_from.value}) and '{to_unit}' "
                f"({dim_to.value}) without an analyte_code to provide molecular weight."
            )
        clean_code = analyte_code.strip().lower()
        if clean_code not in MOLECULAR_WEIGHTS:
            raise IncompatibleUnitsError(
                f"Molecular weight unknown for analyte '{analyte_code}'; cannot convert mass to molar units."
            )
        mw = MOLECULAR_WEIGHTS[clean_code]  # g/mol

        if dim_from == UnitDimension.MASS_CONCENTRATION:
            # Value -> base g/L -> divide by MW (g/mol) -> mol/L -> target unit
            val_in_g_per_l = value * scale_from
            val_in_mol_per_l = val_in_g_per_l / mw
            return val_in_mol_per_l / scale_to
        else:
            # Value -> base mol/L -> multiply by MW (g/mol) -> g/L -> target unit
            val_in_mol_per_l = value * scale_from
            val_in_g_per_l = val_in_mol_per_l * mw
            return val_in_g_per_l / scale_to

    # Case 3: Completely incompatible dimensions
    raise IncompatibleUnitsError(
        f"Incompatible unit conversion requested: '{from_unit}' ({dim_from.value}) "
        f"cannot be converted to '{to_unit}' ({dim_to.value})."
    )
