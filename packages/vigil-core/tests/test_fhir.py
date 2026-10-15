"""
Tests for vigil_core.fhir: HL7 FHIR R4 Patient and Observation mappers.
"""

from vigil_core.fhir import (
    bundle_to_fhir,
    fhir_to_observation,
    fhir_to_patient,
    observation_to_fhir,
    patient_to_fhir,
)


def test_patient_to_fhir_and_round_trip():
    patient_id = "test-pt-12345"
    fhir_res = patient_to_fhir(
        patient_id=patient_id,
        age=52,
        gender="female",
        is_synthetic=True,
    )

    assert fhir_res["resourceType"] == "Patient"
    assert fhir_res["id"] == patient_id
    assert fhir_res["gender"] == "female"
    assert "birthDate" in fhir_res
    assert fhir_res["meta"]["tag"][0]["code"] == "synthetic"

    parsed = fhir_to_patient(fhir_res)
    assert parsed["id"] == patient_id
    assert parsed["gender"] == "female"
    assert parsed["age"] == 52
    assert parsed["is_synthetic"] is True


def test_observation_to_fhir_and_round_trip():
    obs_res = observation_to_fhir(
        analyte_code="ca_15_3",
        value=42.5,
        unit="[iU]/mL",
        patient_id="pt-999",
        effective_datetime="2026-05-10T08:30:00Z",
        is_synthetic=True,
    )

    assert obs_res["resourceType"] == "Observation"
    assert obs_res["status"] == "final"
    assert obs_res["subject"]["reference"] == "Patient/pt-999"
    assert obs_res["effectiveDateTime"] == "2026-05-10T08:30:00Z"
    assert obs_res["valueQuantity"]["value"] == 42.5
    assert obs_res["valueQuantity"]["unit"] == "[iU]/mL"

    # LOINC coding check
    coding = obs_res["code"]["coding"][0]
    assert coding["system"] == "http://loinc.org"
    assert coding["code"] == "83082-8"

    # Reference range
    assert len(obs_res["referenceRange"]) == 1
    assert obs_res["referenceRange"][0]["high"]["value"] == 30.0

    # Parse back
    parsed = fhir_to_observation(obs_res)
    assert parsed["patient_id"] == "pt-999"
    assert parsed["analyte_code"] == "ca_15_3"
    assert parsed["loinc_code"] == "83082-8"
    assert parsed["value"] == 42.5
    assert parsed["unit"] == "[iU]/mL"
    assert parsed["is_synthetic"] is True


def test_bundle_to_fhir():
    patient = patient_to_fhir(patient_id="pt-bundle", age=48)
    obs1 = observation_to_fhir("alt", 28.0, "U/L", "pt-bundle")
    obs2 = observation_to_fhir("creatinine", 0.9, "mg/dL", "pt-bundle")

    bundle = bundle_to_fhir(patient=patient, observations=[obs1, obs2])
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] == 3
    assert len(bundle["entry"]) == 3
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    assert bundle["entry"][1]["resource"]["resourceType"] == "Observation"
    assert bundle["entry"][2]["resource"]["resourceType"] == "Observation"
