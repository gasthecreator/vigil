"""Vigil Core Domain Library.

Clinical domain entities, analyte registry, LOINC/UCUM validation, and FHIR R4 mappers.
"""

from vigil_core.analytes import (
    ANALYTE_REGISTRY,
    AnalyteDefinition,
    AnalyticalSpecification,
    BiologicalVariation,
    PlausibilityBounds,
    PlausibilityResult,
    PlausibilityStatus,
    TargetOrgan,
    calculate_rcv,
    check_plausibility,
    get_analyte,
    list_analytes,
)
from vigil_core.fhir import (
    bundle_to_fhir,
    fhir_to_observation,
    fhir_to_patient,
    observation_to_fhir,
    patient_to_fhir,
)
from vigil_core.units import (
    IncompatibleUnitsError,
    InvalidUnitError,
    UnitConversionError,
    UnitDimension,
    convert_units,
    get_unit_dimension,
    normalize_unit_string,
)

__version__ = "0.1.0-alpha"

__all__ = [
    "ANALYTE_REGISTRY",
    "AnalyteDefinition",
    "BiologicalVariation",
    "AnalyticalSpecification",
    "PlausibilityBounds",
    "PlausibilityStatus",
    "PlausibilityResult",
    "TargetOrgan",
    "get_analyte",
    "list_analytes",
    "calculate_rcv",
    "check_plausibility",
    "UnitDimension",
    "UnitConversionError",
    "IncompatibleUnitsError",
    "InvalidUnitError",
    "convert_units",
    "normalize_unit_string",
    "get_unit_dimension",
    "patient_to_fhir",
    "fhir_to_patient",
    "observation_to_fhir",
    "fhir_to_observation",
    "bundle_to_fhir",
]
