"""
vigil_core.fhir

HL7 FHIR R4 Mappers for Vigil Oncology Decision-Support Platform.
Maps internal patient and longitudinal lab observations to standard FHIR R4
Patient and Observation resources with LOINC and UCUM codings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from vigil_core.analytes import ANALYTE_REGISTRY, get_analyte

LOINC_TO_ANALYTE_CODE = {analyte.loinc_code: analyte.code for analyte in ANALYTE_REGISTRY.values()}


def patient_to_fhir(
    patient_id: str,
    age: Optional[int] = None,
    birth_date: Optional[str] = None,
    gender: Optional[str] = "female",
    is_synthetic: bool = True,
) -> Dict[str, Any]:
    """
    Constructs a standard HL7 FHIR R4 Patient resource.
    """
    resource: Dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(patient_id),
        "identifier": [
            {
                "use": "official",
                "system": "urn:vigil:patient:id",
                "value": str(patient_id),
            }
        ],
        "active": True,
        "gender": gender if gender in ["male", "female", "other", "unknown"] else "unknown",
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"],
            "tag": [
                {
                    "system": "urn:vigil:provenance",
                    "code": "synthetic" if is_synthetic else "clinical",
                    "display": "Synthetic Research Cohort"
                    if is_synthetic
                    else "Clinical Primary Record",
                }
            ],
        },
    }
    if birth_date:
        resource["birthDate"] = birth_date
    elif age is not None:
        # Approximate birth year if only age is known
        approx_year = datetime.now(timezone.utc).year - age
        resource["birthDate"] = f"{approx_year}-01-01"

    return resource


def fhir_to_patient(resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses an HL7 FHIR R4 Patient resource into Vigil internal patient representation.
    """
    if resource.get("resourceType") != "Patient":
        raise ValueError(f"Expected Patient resource, got '{resource.get('resourceType')}'")

    patient_id = resource.get("id")
    if not patient_id and resource.get("identifier"):
        patient_id = resource["identifier"][0].get("value")

    gender = resource.get("gender", "unknown")
    birth_date = resource.get("birthDate")
    age = None
    if birth_date:
        try:
            b_year = int(birth_date.split("-")[0])
            age = datetime.now(timezone.utc).year - b_year
        except Exception:
            pass

    is_synthetic = False
    meta = resource.get("meta", {})
    for tag in meta.get("tag", []):
        if tag.get("code") == "synthetic":
            is_synthetic = True

    return {
        "id": patient_id,
        "gender": gender,
        "birth_date": birth_date,
        "age": age,
        "is_synthetic": is_synthetic,
    }


def observation_to_fhir(
    analyte_code: str,
    value: float,
    unit: str,
    patient_id: str,
    observation_id: Optional[str] = None,
    effective_datetime: Optional[str] = None,
    status: str = "final",
    is_synthetic: bool = True,
) -> Dict[str, Any]:
    """
    Constructs an HL7 FHIR R4 Observation resource for a laboratory measurement.
    """
    analyte = get_analyte(analyte_code)
    obs_id = observation_id or str(uuid4())
    effective_dt = effective_datetime or datetime.now(timezone.utc).isoformat()

    ref_range = []
    if (
        analyte.plausibility.reference_low is not None
        and analyte.plausibility.reference_high is not None
    ):
        ref_range.append(
            {
                "low": {
                    "value": analyte.plausibility.reference_low,
                    "unit": analyte.canonical_unit,
                    "system": "http://unitsofmeasure.org",
                    "code": analyte.canonical_unit,
                },
                "high": {
                    "value": analyte.plausibility.reference_high,
                    "unit": analyte.canonical_unit,
                    "system": "http://unitsofmeasure.org",
                    "code": analyte.canonical_unit,
                },
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/referencerange-meaning",
                            "code": "normal",
                            "display": "Normal Range",
                        }
                    ]
                },
            }
        )

    resource: Dict[str, Any] = {
        "resourceType": "Observation",
        "id": obs_id,
        "status": status,
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": analyte.loinc_code,
                    "display": analyte.name,
                }
            ],
            "text": analyte.name,
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
        },
        "effectiveDateTime": effective_dt,
        "valueQuantity": {
            "value": float(value),
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit,
        },
        "referenceRange": ref_range,
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"],
            "tag": [
                {
                    "system": "urn:vigil:provenance",
                    "code": "synthetic" if is_synthetic else "clinical",
                    "display": "Synthetic Research Cohort"
                    if is_synthetic
                    else "Clinical Observation",
                }
            ],
        },
    }
    return resource


def fhir_to_observation(resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses an HL7 FHIR R4 Observation resource into Vigil internal lab result representation.
    """
    if resource.get("resourceType") != "Observation":
        raise ValueError(f"Expected Observation resource, got '{resource.get('resourceType')}'")

    obs_id = resource.get("id")
    subject_ref = resource.get("subject", {}).get("reference", "")
    patient_id = subject_ref.replace("Patient/", "") if subject_ref else None

    # Resolve LOINC code
    codings = resource.get("code", {}).get("coding", [])
    loinc_code = None
    analyte_code = None
    for c in codings:
        if c.get("system") == "http://loinc.org":
            loinc_code = c.get("code")
            if loinc_code in LOINC_TO_ANALYTE_CODE:
                analyte_code = LOINC_TO_ANALYTE_CODE[loinc_code]
            break

    val_qty = resource.get("valueQuantity", {})
    val = val_qty.get("value")
    unit = val_qty.get("unit") or val_qty.get("code")
    effective_dt = resource.get("effectiveDateTime")

    is_synthetic = False
    meta = resource.get("meta", {})
    for tag in meta.get("tag", []):
        if tag.get("code") == "synthetic":
            is_synthetic = True

    return {
        "id": obs_id,
        "patient_id": patient_id,
        "loinc_code": loinc_code,
        "analyte_code": analyte_code,
        "value": float(val) if val is not None else None,
        "unit": unit,
        "effective_datetime": effective_dt,
        "is_synthetic": is_synthetic,
    }


def bundle_to_fhir(
    patient: Dict[str, Any],
    observations: List[Dict[str, Any]],
    bundle_type: str = "collection",
) -> Dict[str, Any]:
    """
    Assembles Patient and Observation resources into an HL7 FHIR R4 Bundle.
    """
    entries = [{"resource": patient}]
    for obs in observations:
        entries.append({"resource": obs})

    return {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": bundle_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "entry": entries,
    }
