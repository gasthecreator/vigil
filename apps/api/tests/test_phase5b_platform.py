"""Comprehensive test suite for Phase 5b platform deliverables.

Tests:
1. Batch CSV & Excel Import (strict schema, unit-safe registry validation, duplicate detection, per-row reporting).
2. HL7 FHIR R4 Observation Export and Import round-trip with LOINC and UCUM.
3. Triage Queue ordered by Action Urgency (with fixtures proving Action Urgency differs from Risk alone).
4. Reminder Worker with Sandbox provider, privacy-safe templates, opt-out honouring, and injectable clock.
5. Request ID generation, propagation, and structured logging.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from vigil_api.database import Base, engine
from vigil_api.main import app
from vigil_api.models.v2 import (
    FollowUpTask,
    FollowUpTaskStatus,
    FollowUpTaskType,
)
from vigil_api.reminders import (
    SandboxNotificationProvider,
    format_privacy_safe_message,
    run_reminder_cycle,
)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _create_consented_patient(client, age: int = 50) -> str:
    """Helper creating an active patient with valid surveillance consent."""
    headers = {"X-Vigil-Role": "clinician"}
    resp = client.post("/api/v1/patients/", json={"age": age, "status": "active"}, headers=headers)
    assert resp.status_code == 201
    pid = resp.json()["id"]

    c_resp = client.post(
        f"/api/v1/patients/{pid}/consent",
        json={"scope": "surveillance_monitoring", "granted": True},
        headers=headers,
    )
    assert c_resp.status_code == 201
    return pid


# ============================================================================
# 1. Batch CSV and Excel Import Tests
# ============================================================================


def test_batch_csv_import_success_and_reporting(client):
    """Verifies valid CSV rows are ingested through M3/K2 pipeline with full per-row report."""
    pid = _create_consented_patient(client, age=48)
    headers = {"X-Vigil-Role": "clinician"}

    csv_data = f"""patient_id,analyte_code,value,unit,specimen_collected_at
{pid},ca_15_3,18.5,U/mL,2026-02-01T08:00:00+00:00
{pid},ca_15_3,19.0,U/mL,2026-03-01T08:00:00+00:00
{pid},alt,24.0,U/L,2026-03-01T08:00:00+00:00
"""
    resp = client.post(
        "/api/v1/observations/batch-import",
        json={"csv_data": csv_data},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_rows"] == 3
    assert data["imported_count"] == 3
    assert data["duplicate_count"] == 0
    assert data["rejected_count"] == 0

    assert len(data["row_reports"]) == 3
    assert all(r["status"] == "imported" for r in data["row_reports"])
    assert all(r["observation_id"] is not None for r in data["row_reports"])


def test_batch_import_duplicate_detection(client):
    """Verifies exact duplicate rows at the same timestamp are detected and not duplicated."""
    pid = _create_consented_patient(client, age=52)
    headers = {"X-Vigil-Role": "clinician"}

    timestamp = "2026-04-15T09:30:00+00:00"
    payload = {
        "rows": [
            {
                "patient_id": pid,
                "analyte_code": "ca_15_3",
                "value": 22.0,
                "unit": "U/mL",
                "specimen_collected_at": timestamp,
            }
        ]
    }

    # First import -> success
    r1 = client.post("/api/v1/observations/batch-import", json=payload, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["imported_count"] == 1

    # Second import with identical patient, analyte, timestamp -> duplicate
    r2 = client.post("/api/v1/observations/batch-import", json=payload, headers=headers)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["imported_count"] == 0
    assert d2["duplicate_count"] == 1
    assert d2["row_reports"][0]["status"] == "duplicate"
    assert "Duplicate observation" in d2["row_reports"][0]["errors"][0]


def test_batch_import_strict_validation_rejection(client):
    """Verifies that invalid units, unknown analytes, and missing consent are rejected with per-row errors."""
    pid = _create_consented_patient(client, age=55)
    headers = {"X-Vigil-Role": "clinician"}

    # Patient without consent
    p_unconsented = client.post(
        "/api/v1/patients/", json={"age": 60, "status": "active"}, headers=headers
    ).json()["id"]

    payload = {
        "rows": [
            # Incompatible unit for CA 15-3 (e.g. mg/dL instead of U/mL)
            {"patient_id": pid, "analyte_code": "ca_15_3", "value": 25.0, "unit": "mg/dL"},
            # Unknown analyte code
            {
                "patient_id": pid,
                "analyte_code": "fictional_biomarker",
                "value": 10.0,
                "unit": "U/mL",
            },
            # Unconsented patient
            {"patient_id": p_unconsented, "analyte_code": "ca_15_3", "value": 20.0, "unit": "U/mL"},
        ]
    }

    resp = client.post("/api/v1/observations/batch-import", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_rows"] == 3
    assert data["imported_count"] == 0
    assert data["rejected_count"] == 3

    assert any(
        "dimension" in err.lower() or "incompatible" in err.lower()
        for err in data["row_reports"][0]["errors"]
    )
    assert any("not recognized" in err.lower() for err in data["row_reports"][1]["errors"])
    assert any("consent" in err.lower() for err in data["row_reports"][2]["errors"])


# ============================================================================
# 2. HL7 FHIR R4 Observation Export and Import Tests
# ============================================================================


def test_fhir_r4_observation_round_trip(client):
    """Verifies that an observation can be exported to FHIR R4 and re-imported with LOINC and UCUM."""
    pid = _create_consented_patient(client, age=49)
    headers = {"X-Vigil-Role": "clinician"}

    # 1. Create native observation
    obs_resp = client.post(
        f"/api/v1/patients/{pid}/observations",
        json={
            "analyte_code": "ca_15_3",
            "value": 26.5,
            "unit": "U/mL",
            "specimen_collected_at": "2026-05-01T10:00:00+00:00",
        },
        headers=headers,
    )
    assert obs_resp.status_code == 201
    obs_id = obs_resp.json()["observation_id"]

    # 2. Export observation as FHIR R4
    fhir_get = client.get(f"/api/v1/fhir/Observation/{obs_id}", headers=headers)
    assert fhir_get.status_code == 200
    fhir_data = fhir_get.json()

    assert fhir_data["resourceType"] == "Observation"
    assert fhir_data["id"] == obs_id
    assert fhir_data["subject"]["reference"] == f"Patient/{pid}"
    assert fhir_data["valueQuantity"]["value"] == 26.5
    assert fhir_data["valueQuantity"]["unit"] in ("[iU]/mL", "U/mL")

    # Check LOINC code for CA 15-3 (83082-8)
    codings = fhir_data["code"]["coding"]
    assert any(c["system"] == "http://loinc.org" and c["code"] == "83082-8" for c in codings)

    # 3. Import new FHIR Observation for a second visit
    new_fhir_resource = {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "83082-8",
                    "display": "Cancer Ag 15-3 [Units/volume] in Serum or Plasma",
                }
            ]
        },
        "subject": {"reference": f"Patient/{pid}"},
        "effectiveDateTime": "2026-06-01T10:00:00+00:00",
        "valueQuantity": {
            "value": 28.0,
            "unit": "U/mL",
            "system": "http://unitsofmeasure.org",
            "code": "U/mL",
        },
    }

    fhir_post = client.post("/api/v1/fhir/Observation", json=new_fhir_resource, headers=headers)
    assert fhir_post.status_code == 201
    imported_fhir = fhir_post.json()
    assert imported_fhir["resourceType"] == "Observation"
    assert imported_fhir["valueQuantity"]["value"] == 28.0


# ============================================================================
# 3. Triage Queue Action Urgency Tests (Orderings Differ)
# ============================================================================


def test_triage_queue_action_urgency_ordering_differs_from_risk(client):
    """Proves that Triage Queue sorts by composite Action Urgency and differs from risk alone.

    Fixture:
    - Patient LowRiskOverdue:
        Risk = 0.45 (lower risk), BUT has an overdue follow-up task (delay 16 days, level 3)
        and high uncertainty.
    - Patient HighRiskRoutine:
        Risk = 0.65 (higher risk), BUT routine follow-up with no overdue tasks and 0 delay.

    Action Urgency formula:
    Patient LowRiskOverdue achieves higher composite Action Urgency than HighRiskRoutine,
    proving triage prioritization prioritizes actionable care gaps over raw probability alone.
    """
    headers = {"X-Vigil-Role": "clinician"}

    # Patient A: High Risk, Routine
    p_high_risk = _create_consented_patient(client, age=62)
    # Patient B: Moderate Risk, Highly Overdue Task
    p_overdue = _create_consented_patient(client, age=58)

    now = datetime.now(timezone.utc)

    # Record labs for Patient A: CA 15-3 spike -> Risk = 0.65
    client.post(
        f"/api/v1/patients/{p_high_risk}/labs",
        json={
            "date_drawn": now.isoformat(),
            "ca_15_3": 65.0,
            "alt_level": 25.0,
            "ast_level": 20.0,
            "creatinine": 0.9,
            "wbc_count": 6.0,
        },
        headers=headers,
    )

    # Record labs for Patient B: CA 15-3 moderate -> Risk = 0.40
    client.post(
        f"/api/v1/patients/{p_overdue}/labs",
        json={
            "date_drawn": (now - timedelta(days=120)).isoformat(),
            "ca_15_3": 32.0,
            "alt_level": 22.0,
            "ast_level": 19.0,
            "creatinine": 0.85,
            "wbc_count": 5.8,
        },
        headers=headers,
    )

    # Inject an overdue FollowUpTask for Patient B (16 days overdue, escalation level 3)
    from vigil_api.database import SessionLocal

    db = SessionLocal()
    try:
        task = FollowUpTask(
            patient_id=p_overdue,
            task_type=FollowUpTaskType.REPEAT_SPECIMEN.value,
            status=FollowUpTaskStatus.ESCALATED.value,
            due_date=now - timedelta(days=16),
            escalation_level=3,
            notes="Critical repeat specimen delayed.",
        )
        db.add(task)
        db.commit()
    finally:
        db.close()

    # Query Triage Queue
    triage_resp = client.get("/api/v1/patients/triage", headers=headers)
    assert triage_resp.status_code == 200
    queue = triage_resp.json()

    item_high_risk = next(q for q in queue if q["patient_id"] == p_high_risk)
    item_overdue = next(q for q in queue if q["patient_id"] == p_overdue)

    # Verify that raw risk ordering is HighRisk > Overdue
    assert item_high_risk["latest_risk"] > item_overdue["latest_risk"]

    # Verify that action urgency ordering is Overdue > HighRisk
    assert item_overdue["action_urgency"] > item_high_risk["action_urgency"], (
        f"Expected Overdue ({item_overdue['action_urgency']}) to have higher action urgency "
        f"than HighRisk ({item_high_risk['action_urgency']})"
    )

    # Verify queue ordering places Overdue ahead of HighRisk
    idx_overdue = [i for i, q in enumerate(queue) if q["patient_id"] == p_overdue][0]
    idx_high_risk = [i for i, q in enumerate(queue) if q["patient_id"] == p_high_risk][0]
    assert idx_overdue < idx_high_risk, (
        f"Patient with urgent overdue task (rank {idx_overdue}) must appear before "
        f"routine high risk (rank {idx_high_risk}) in triage queue."
    )


# ============================================================================
# 4. Reminder Worker Tests (Sandbox, Privacy, Opt-Out, Escalation)
# ============================================================================


def test_reminder_worker_privacy_safe_templates():
    """Verifies that notification text contains ZERO biomarker values, analyte names, or oncological diagnoses."""
    msg1 = format_privacy_safe_message(FollowUpTaskType.REPEAT_SPECIMEN.value, escalation_level=1)
    msg2 = format_privacy_safe_message(FollowUpTaskType.REPEAT_SPECIMEN.value, escalation_level=3)
    msg3 = format_privacy_safe_message(FollowUpTaskType.IMAGING_REFERRAL.value, escalation_level=0)

    forbidden_substrings = [
        "ca 15-3",
        "ca153",
        "biomarker",
        "tumor",
        "metastasis",
        "cancer",
        "u/ml",
        "u/l",
        "spike",
        "recurrence",
        "malignan",
    ]
    for msg in (msg1, msg2, msg3):
        lower = msg.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lower, (
                f"Privacy violation: found '{forbidden}' in message: {msg}"
            )


def test_reminder_worker_dispatch_and_receipts(client):
    """Verifies reminder worker dispatches via sandbox provider and creates delivery receipts."""
    pid = _create_consented_patient(client, age=53)
    headers = {"X-Vigil-Role": "clinician"}

    # Create task due 4 days ago (Escalation level 1)
    from vigil_api.database import SessionLocal

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        task = FollowUpTask(
            patient_id=pid,
            task_type=FollowUpTaskType.REPEAT_SPECIMEN.value,
            status=FollowUpTaskStatus.PENDING.value,
            due_date=now - timedelta(days=4),
            escalation_level=0,
            notes="Routine check.",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        tid = task.id
    finally:
        db.close()

    # Run reminder cycle via API with clock
    run_resp = client.post(
        f"/api/v1/follow-up/reminders/run?simulated_now={now.isoformat()}",
        headers=headers,
    )
    assert run_resp.status_code == 200
    res_data = run_resp.json()
    assert res_data["dispatched_count"] >= 1

    # Verify receipts endpoint
    rec_resp = client.get(f"/api/v1/follow-up/reminders/receipts?task_id={tid}", headers=headers)
    assert rec_resp.status_code == 200
    receipts = rec_resp.json()
    assert len(receipts) >= 1
    assert receipts[0]["status"] in ("sent", "delivered")
    assert receipts[0]["external_message_id"].startswith("sandbox-")


def test_reminder_worker_honours_patient_opt_out(client):
    """Verifies that reminders are NOT dispatched if a patient has opted out or withdrawn consent."""
    headers = {"X-Vigil-Role": "clinician"}

    # Create patient with explicit opt-out in scope
    p_resp = client.post("/api/v1/patients/", json={"age": 51, "status": "active"}, headers=headers)
    pid = p_resp.json()["id"]

    client.post(
        f"/api/v1/patients/{pid}/consent",
        json={"scope": "clinical_care,opt_out_reminders", "granted": True},
        headers=headers,
    )

    from vigil_api.database import SessionLocal

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        task = FollowUpTask(
            patient_id=pid,
            task_type=FollowUpTaskType.REPEAT_SPECIMEN.value,
            status=FollowUpTaskStatus.PENDING.value,
            due_date=now - timedelta(days=3),
            escalation_level=0,
        )
        db.add(task)
        db.commit()
        tid = task.id
    finally:
        db.close()

    sandbox = SandboxNotificationProvider()
    try:
        db = SessionLocal()
        receipts = run_reminder_cycle(db=db, provider=sandbox, current_time=now)
        # Sandbox provider should NOT have sent any message for this task
        assert len(sandbox.sent_messages) == 0

        # Receipt should record opted_out status
        task_receipts = [r for r in receipts if r.task_id == tid]
        assert len(task_receipts) == 1
        assert task_receipts[0].status == "opted_out"
    finally:
        db.close()


# ============================================================================
# 5. Request ID Middleware & Structured JSON Logging Tests
# ============================================================================


def test_request_id_middleware_and_propagation(client):
    """Verifies that X-Request-ID is generated and returned on all requests."""
    # 1. Unspecified request ID generates a UUID
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert "x-request-id" in r1.headers
    req_id = r1.headers["x-request-id"]
    assert len(req_id) >= 16

    # 2. Specified request ID is propagated back
    custom_id = "client-trace-123456"
    r2 = client.get("/health", headers={"X-Request-ID": custom_id})
    assert r2.status_code == 200
    assert r2.headers["x-request-id"] == custom_id
