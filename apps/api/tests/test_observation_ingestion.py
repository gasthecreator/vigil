"""Unit-Safe Observation Ingestion and Safety Invariants Test Suite.

Implements Master Plan §6.0 (M0), §6.6 (M6), §11, and Phase 5a Ingestion requirements:
- Unit-safe validation against Analyte Registry (strict rejection of invalid/incompatible units).
- Negative and zero value rejection (strictly positive concentration).
- M3 Plausibility Adjudication integration.
- K2 SequentialDetector state updates and per-patient persistence.
- M5 Clinician narrative note provenance verification.
- Model versions and SHA-256 input hash storage in RiskAssessment.
- No-Dismissal Safety Invariant: surprising/abnormal findings must produce an Alert and FollowUpTask.
- Verification that responses carry the mandatory synthetic flag.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from vigil_api.auth import create_access_token
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import (
    Alert,
    ConsentRecord,
    Facility,
    FollowUpTask,
    Observation,
    Patient,
    RiskAssessment,
    UserRole,
)


@pytest.fixture
def ingestion_db(tmp_path):
    """Set up an isolated database for observation ingestion tests."""
    db_file = tmp_path / "test_ingest.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        fac = Facility(
            id="fac-onc",
            name="Lagos Oncology",
            code="LAG-01",
            country="NG",
            tier="tertiary",
            active=True,
            created_at=now,
        )
        session.add(fac)

        pat = Patient(
            id="pat-surv-01",
            facility_id="fac-onc",
            mrn="MRN-SURV-01",
            biological_sex="female",
            primary_cancer_type="breast",
            synthetic=True,
            status="active",
            created_at=now - timedelta(days=180),
            updated_at=now - timedelta(days=180),
        )
        session.add(pat)

        # Active surveillance consent
        consent = ConsentRecord(
            patient_id="pat-surv-01",
            consent_type="surveillance_monitoring",
            granted=True,
            granted_at=now - timedelta(days=180),
            scope="full",
        )
        session.add(consent)
        session.commit()

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


@pytest.fixture
def clinician_auth_headers():
    token = create_access_token(subject="dr_kemi", role=UserRole.CLINICIAN.value)
    return {"Authorization": f"Bearer {token}"}


def test_unit_safe_ingestion_rejection(ingestion_db, clinician_auth_headers):
    """Verify that invalid units, incompatible dimensions, and decimal errors are rejected with HTTP 422."""
    client, _ = ingestion_db

    # 1. Unknown / invalid unit
    r_bad_unit = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json={"analyte_code": "ca_15_3", "value": 25.0, "unit": "smoots/hour"},
        headers=clinician_auth_headers,
    )
    assert r_bad_unit.status_code == 422
    assert "Unit validation failed" in r_bad_unit.json()["detail"]
    assert "Silent unit coercion is forbidden" in r_bad_unit.json()["detail"]

    # 2. Incompatible dimension (seconds for a concentration marker)
    r_dim = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json={"analyte_code": "ca_15_3", "value": 25.0, "unit": "s"},
        headers=clinician_auth_headers,
    )
    assert r_dim.status_code == 422
    assert (
        "Incompatible" in r_dim.json()["detail"]
        or "Unit validation failed" in r_dim.json()["detail"]
    )

    # 3. Negative value (unphysiological error)
    r_neg = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json={"analyte_code": "ca_15_3", "value": -10.0, "unit": "U/mL"},
        headers=clinician_auth_headers,
    )
    assert r_neg.status_code == 422
    assert "strictly positive" in r_neg.json()["detail"]

    # 4. Unknown analyte code
    r_unknown_analyte = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json={"analyte_code": "fictional_biomarker_99", "value": 15.0, "unit": "U/mL"},
        headers=clinician_auth_headers,
    )
    assert r_unknown_analyte.status_code == 422
    assert "not found in registry" in r_unknown_analyte.json()["detail"]


def test_normal_observation_ingestion_and_k2_update(ingestion_db, clinician_auth_headers):
    """Verify clean ingestion of normal observation, M3 adjudication, and K2 persistence."""
    client, engine = ingestion_db

    payload = {
        "analyte_code": "ca_15_3",
        "value": 18.5,
        "unit": "U/mL",
    }
    r = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json=payload,
        headers=clinician_auth_headers,
    )
    assert r.status_code == 201
    data = r.json()

    # 1. Structural fields & mandatory synthetic flag
    assert data["synthetic"] is True
    assert data["analyte_code"] == "ca_15_3"
    assert data["canonical_value"] == 18.5
    assert data["canonical_unit"] == "[iU]/mL"
    assert data["raw_value"] == 18.5
    assert data["raw_unit"] == "U/mL"
    assert data["plausibility_status"] == "valid_normal"

    # 2. RiskAssessment model versions and input hash
    risk = data["risk_assessment"]
    assert risk["model_versions"] == {
        "M3": "1.0",
        "M3-assumptions": "not_applied",
        "M3-assumptions-sha256": "not_applied",
        "K2": "1.0",
        "M5": "1.0",
    }
    assert len(risk["input_hash"]) == 64
    assert risk["adjudicated_action"] == "abstain"
    assert risk["abstention"] is True
    assert risk["abstention_reason"] == "insufficient_history"
    assert risk["score"] is None
    assert "without structured rationale facts" in risk["clinical_note"]
    explainer = client.get(
        f"/api/v1/patients/pat-surv-01/observations/{data['observation_id']}/explainer",
        headers=clinician_auth_headers,
    )
    assert explainer.status_code == 200
    assert explainer.json()["verdict"] == "abstain"
    assert "not enough history" in explainer.json()["headline"].lower()

    # The first value is never used as its own personalized baseline. A second
    # temporally later draw enables an ordinary, non-abstaining comparison.
    later = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json={
            "analyte_code": "ca_15_3",
            "value": 18.7,
            "unit": "U/mL",
            "specimen_collected_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
        headers=clinician_auth_headers,
    )
    assert later.status_code == 201
    assert later.json()["risk_assessment"]["abstention"] is False
    original_explainer = client.get(
        f"/api/v1/patients/pat-surv-01/observations/{data['observation_id']}/explainer",
        headers=clinician_auth_headers,
    )
    assert original_explainer.status_code == 200
    assert original_explainer.json()["verdict"] == "abstain"

    # 3. Routine normal observation does not create alert or task
    assert data["alert"] is None
    assert data["follow_up_task"] is None

    # 4. Verify patient's detector state was persisted in the database
    with Session(engine) as session:
        pat = session.execute(select(Patient).where(Patient.id == "pat-surv-01")).scalar_one()
        assert pat.detector_state is not None
        assert set(pat.detector_state["analytes"]) == {"ca_15_3"}
        assert len(pat.detector_state["analytes"]["ca_15_3"]["history"]) == 2


def test_k2_ingestion_keeps_analyte_histories_independent(ingestion_db, clinician_auth_headers):
    client, engine = ingestion_db
    for analyte_code, value, unit in (
        ("ca_15_3", 20.0, "U/mL"),
        ("cea", 3.0, "ng/mL"),
    ):
        response = client.post(
            "/api/v1/patients/pat-surv-01/observations",
            json={"analyte_code": analyte_code, "value": value, "unit": unit},
            headers=clinician_auth_headers,
        )
        assert response.status_code == 201

    with Session(engine) as session:
        patient = session.execute(
            select(Patient).where(Patient.id == "pat-surv-01")
        ).scalar_one()
        analyte_states = patient.detector_state["analytes"]
        assert set(analyte_states) == {"ca_15_3", "cea"}
        assert len(analyte_states["ca_15_3"]["history"]) == 1
        assert len(analyte_states["cea"]["history"]) == 1


def test_surprising_observation_enforces_no_dismissal_invariant(
    ingestion_db, clinician_auth_headers
):
    """Verify that surprising results (e.g. gross error 10x spike) yield an Alert and FollowUpTask."""
    client, engine = ingestion_db

    # Baseline draw: 20 U/mL
    client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json={"analyte_code": "ca_15_3", "value": 20.0, "unit": "U/mL"},
        headers=clinician_auth_headers,
    )

    # Surprising gross spike: 200 U/mL (10x ratio -> M3 flags needs_repeat)
    payload_spike = {
        "analyte_code": "ca_15_3",
        "value": 200.0,
        "unit": "U/mL",
    }
    r = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json=payload_spike,
        headers=clinician_auth_headers,
    )
    assert r.status_code == 201
    data = r.json()

    assert data["synthetic"] is True
    assert data["adjudicated_action"] == "needs_repeat"
    assert data["adjudicated_action"] != "dismissed"  # Safety Invariant

    # Alert must be created
    alert_info = data["alert"]
    assert alert_info is not None
    assert alert_info["alert_type"] == "lab_error_repeat"
    assert alert_info["status"] == "open"

    # Follow-up task must be created
    task_info = data["follow_up_task"]
    assert task_info is not None
    assert task_info["task_type"] == "repeat_specimen"
    assert task_info["status"] == "pending"
    assert task_info["escalation_level"] == 0

    # Verify database layer invariants
    with Session(engine) as session:
        stored_risk = session.execute(
            select(RiskAssessment).where(RiskAssessment.id == data["risk_assessment"]["id"])
        ).scalar_one()
        assert stored_risk.adjudicated_action == "needs_repeat"
        assert stored_risk.adjudicated_action != "dismissed"
        stored_obs = session.execute(
            select(Observation).where(Observation.id == data["observation_id"])
        ).scalar_one()
        assert stored_obs.status != "dismissed"

        stored_alert = session.execute(
            select(Alert).where(Alert.id == alert_info["id"])
        ).scalar_one()
        assert stored_alert.patient_id == "pat-surv-01"

        stored_task = session.execute(
            select(FollowUpTask).where(FollowUpTask.id == task_info["id"])
        ).scalar_one()
        assert stored_task.alert_id == stored_alert.id


def test_backfilled_measurement_does_not_use_future_observation_as_m3_history(
    ingestion_db, clinician_auth_headers
):
    client, engine = ingestion_db
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add(
            Observation(
                id="obs-future",
                patient_id="pat-surv-01",
                analyte_code="ca_15_3",
                value=40.0,
                unit="[iU]/mL",
                specimen_collected_at=now + timedelta(days=5),
                result_received_at=now,
                plausibility_status="valid_normal",
                raw_value=40.0,
                raw_unit="U/mL",
                status="valid",
                created_at=now,
            )
        )
        session.commit()

    response = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json={
            "analyte_code": "ca_15_3",
            "value": 22.0,
            "unit": "U/mL",
            "specimen_collected_at": (now - timedelta(days=2)).isoformat(),
        },
        headers=clinician_auth_headers,
    )

    assert response.status_code == 201
    risk = response.json()["risk_assessment"]
    assert risk["abstention"] is True
    assert risk["abstention_reason"] == "insufficient_history"
    assert risk["score"] is None


def test_real_patient_ingestion_preserves_non_synthetic_provenance(
    ingestion_db, clinician_auth_headers
):
    client, engine = ingestion_db
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        patient = session.execute(select(Patient).where(Patient.id == "pat-surv-01")).scalar_one()
        patient.synthetic = False
        session.add(
            Observation(
                id="obs-real-prior",
                patient_id=patient.id,
                analyte_code="ca_15_3",
                value=20.0,
                unit="[iU]/mL",
                specimen_collected_at=now - timedelta(days=30),
                result_received_at=now - timedelta(days=30),
                plausibility_status="valid_normal",
                raw_value=20.0,
                raw_unit="U/mL",
                status="valid",
                created_at=now - timedelta(days=30),
            )
        )
        session.commit()

    response = client.post(
        "/api/v1/patients/pat-surv-01/observations",
        json={"analyte_code": "ca_15_3", "value": 23.0, "unit": "U/mL"},
        headers=clinician_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["synthetic"] is False
    assert data["risk_assessment"]["abstention"] is True
    assert data["risk_assessment"]["abstention_reason"] == "clinical_validation_unavailable"
    assert data["risk_assessment"]["score"] is None
    assert data["adjudicated_action"] == "abstain"
    listed = client.get(
        "/api/v1/patients/pat-surv-01/observations", headers=clinician_auth_headers
    )
    assert listed.status_code == 200
    assert listed.json()[-1]["quality_flags"]["action"] == "abstain"
    history = client.get(
        "/api/v1/patients/pat-surv-01/risk-history", headers=clinician_auth_headers
    )
    assert history.status_code == 200
    assert history.json()[0]["score"] is None
    assert history.json()[0]["abstention_reason"] == "clinical_validation_unavailable"
    explainer = client.get(
        f"/api/v1/patients/pat-surv-01/observations/{data['observation_id']}/explainer",
        headers=clinician_auth_headers,
    )
    assert explainer.status_code == 200
    assert explainer.json()["synthetic"] is False
    assert explainer.json()["verdict"] == "abstain"
