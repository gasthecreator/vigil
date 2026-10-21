"""Unit and Integration tests for Treatment Continuity & Radiotherapy Triage (M7)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

# Setup test environment
os.environ["ENVIRONMENT"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy.orm import Session
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import (
    ConsentRecord,
    CourseStatus,
    Facility,
    LinacMachine,
    MachineStatus,
    Patient,
    RadiotherapyContext,
    RadiotherapyCourse,
    User,
    UserRole,
)


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_continuity.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        # Seed facility
        fac = Facility(
            id="FAC-01", name="UCH Ibadan Oncology Center", code="UCH-ONC", tier="tertiary"
        )
        session.add(fac)

        # Seed users
        clinician = User(
            id="USR-DR-01",
            username="dr_folashade",
            email="dr@uch.edu.ng",
            role=UserRole.CLINICIAN.value,
            full_name="Dr. Folashade Adebayo",
            hashed_password="pw",
            facility_id=fac.id,
        )
        nurse = User(
            id="USR-NURSE-01",
            username="nurse_clerk",
            email="nurse@uch.edu.ng",
            role=UserRole.NURSE_CLERK.value,
            full_name="Nurse Clerk",
            hashed_password="pw",
            facility_id=fac.id,
        )
        admin = User(
            id="USR-ADMIN-01",
            username="admin_lead",
            email="admin@uch.edu.ng",
            role=UserRole.ADMIN.value,
            full_name="Admin Lead",
            hashed_password="pw",
            facility_id=fac.id,
        )
        session.add_all([clinician, nurse, admin])

        # Seed patients
        p1 = Patient(
            id="PAT-CONT-01", biological_sex="female", primary_cancer_type="breast", age=50, synthetic=True
        )
        p2 = Patient(
            id="PAT-CONT-02", biological_sex="female", primary_cancer_type="breast", age=62, synthetic=True
        )
        p_unconsented = Patient(
            id="PAT-NO-CONSENT", biological_sex="female", primary_cancer_type="breast", age=45, synthetic=True
        )
        session.add_all([p1, p2, p_unconsented])

        # Consent
        c1 = ConsentRecord(patient_id=p1.id, granted=True, scope="full", granted_at=now)
        c2 = ConsentRecord(patient_id=p2.id, granted=True, scope="full", granted_at=now)
        session.add_all([c1, c2])

        # Seed machines
        m1 = LinacMachine(
            id="LINAC-01",
            facility_id=fac.id,
            machine_name="LINAC-01 (Elekta)",
            daily_slot_capacity=16,
            status=MachineStatus.OPERATIONAL.value,
        )
        m2 = LinacMachine(
            id="LINAC-02",
            facility_id=fac.id,
            machine_name="LINAC-02 (Varian)",
            daily_slot_capacity=16,
            status=MachineStatus.DOWN.value,
            downtime_started_at=now - timedelta(days=2),
            expected_return_at=now + timedelta(days=5),
        )
        session.add_all([m1, m2])

        # Seed radiotherapy courses
        rtc1 = RadiotherapyCourse(
            id="RTC-001",
            patient_id=p1.id,
            assigned_machine_id=m1.id,
            clinical_context=RadiotherapyContext.ADJUVANT_POST_LUMPECTOMY.value,
            total_fractions=15,
            fractions_delivered=0,
            prescribed_start_date=now - timedelta(days=14),
            scheduled_start_date=now - timedelta(days=7),
            urgency_tier="routine",
            status=CourseStatus.PENDING.value,
            baseline_subgroup="subgroup_a",
        )
        rtc2 = RadiotherapyCourse(
            id="RTC-002",
            patient_id=p2.id,
            assigned_machine_id=m2.id,
            clinical_context=RadiotherapyContext.CURATIVE_TNBC.value,
            total_fractions=25,
            fractions_delivered=5,
            prescribed_start_date=now - timedelta(days=21),
            scheduled_start_date=now - timedelta(days=3),
            urgency_tier="urgent",
            status=CourseStatus.IN_PROGRESS.value,
            baseline_subgroup="subgroup_b",
        )
        session.add_all([rtc1, rtc2])
        session.commit()

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_and_update_linac_machines(client):
    """Test listing LINAC machines and updating machine status with audit logging."""
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"}

    # 1. List machines
    res = client.get("/api/v1/continuity/machines", headers=headers)
    assert res.status_code == 200
    machines = res.json()
    assert len(machines) == 2
    assert any(m["id"] == "LINAC-01" and m["status"] == "operational" for m in machines)
    assert any(m["id"] == "LINAC-02" and m["status"] == "down" for m in machines)

    # 2. Update machine status to operational
    patch_res = client.post(
        "/api/v1/continuity/machines/LINAC-02/status",
        json={
            "status": "operational",
            "reason": "Magnetron replaced and beam calibration verified",
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["status"] == "operational"
    assert updated["downtime_started_at"] is None


def test_create_and_list_radiotherapy_courses(client):
    """Test enrolling a patient into an RT course and calculating delay harm."""
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"}

    # 1. Create a course
    prescribed_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    create_res = client.post(
        "/api/v1/continuity/courses",
        json={
            "patient_id": "PAT-CONT-01",
            "clinical_context": "adjuvant_post_mastectomy",
            "total_fractions": 25,
            "prescribed_start_date": prescribed_date,
            "urgency_tier": "routine",
            "baseline_subgroup": "age_lt_50",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    course_data = create_res.json()
    assert course_data["clinical_context"] == "adjuvant_post_mastectomy"
    assert course_data["total_fractions"] == 25

    # 2. List courses
    list_res = client.get("/api/v1/continuity/courses?patient_id=PAT-CONT-01", headers=headers)
    assert list_res.status_code == 200
    courses = list_res.json()
    assert len(courses) >= 1
    assert courses[0]["current_delay_days"] >= 0
    assert courses[0]["expected_excess_harm"] >= 0.0


def test_schedule_solve_cp_sat(client):
    """The CP-SAT research optimiser still works when explicitly requested by an administrator."""
    headers = {"X-Vigil-Role": "admin", "X-Vigil-User-Id": "USR-ADMIN-01"}

    solve_res = client.post(
        "/api/v1/continuity/schedule/solve",
        json={
            "method": "cpsat_research",
            "horizon_days": 14,
            "fairness_disparity_bound": 5.0,
            "max_wait_days": 30,
            "stability_penalty": 0.01,
        },
        headers=headers,
    )
    assert solve_res.status_code == 200
    sol = solve_res.json()
    assert sol["method"] == "cpsat_research"
    assert sol["validation_status"] == "unvalidated in simulation"
    assert sol["fairness_bound_enforced"] is True
    assert sol["status"] in ("OPTIMAL", "FEASIBLE")
    assert sol["solver_time_seconds"] > 0
    assert len(sol["assignments"]) >= 2
    assert sol["fairness_disparity"] <= 5.0
    for a in sol["assignments"]:
        assert a["patient_id"] in ("PAT-CONT-01", "PAT-CONT-02")
        assert a["marginal_harm"] >= 0.0
        assert len(a["explanation"]) > 0


def test_schedule_solve_defaults_to_explainable_urgency_ranking(client):
    """ADR-0019: the default method is the urgency ranking; the ongoing course ranks first."""
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"}
    res = client.post("/api/v1/continuity/schedule/solve", json={}, headers=headers)
    assert res.status_code == 200
    sol = res.json()
    assert sol["method"] == "urgency_ranking"
    assert sol["method_label"] == "Explainable urgency ranking"
    assert sol["fairness_bound_enforced"] is False
    assert "no real-data validation" in sol["validation_status"]
    assert sol["synthetic"] is True
    by_course = {a["course_id"]: a for a in sol["assignments"]}
    # RTC-002 is in progress (5/25 fractions) -> priority 1; RTC-001 waits.
    assert by_course["RTC-002"]["priority_rank"] == 1
    assert by_course["RTC-001"]["priority_rank"] == 2
    assert "course in progress" in by_course["RTC-002"]["explanation"]
    assert by_course["RTC-002"]["start_day"] == 0


def test_cpsat_research_method_is_not_available_to_clinicians(client):
    """The unvalidated optimiser is a server-side opt-in, not a UI toggle."""
    for role, user in (
        ("clinician", "USR-DR-01"),
        ("quality_lead", "USR-DR-01"),
    ):
        res = client.post(
            "/api/v1/continuity/schedule/solve",
            json={"method": "cpsat_research"},
            headers={"X-Vigil-Role": role, "X-Vigil-User-Id": user},
        )
        assert res.status_code == 403, (role, res.text)
        assert "research module" in res.json()["detail"]


def test_cpsat_research_method_operator_opt_in(client, monkeypatch):
    monkeypatch.setenv("VIGIL_ENABLE_RESEARCH_SCHEDULER", "1")
    res = client.post(
        "/api/v1/continuity/schedule/solve",
        json={"method": "cpsat_research", "horizon_days": 7},
        headers={"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"},
    )
    assert res.status_code == 200
    assert res.json()["validation_status"] == "unvalidated in simulation"


def test_urgency_ranking_warns_when_flagged_course_not_started(client):
    """A clinician-flagged urgent course that the rule cannot start inside its bound is surfaced."""
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"}
    created = client.post(
        "/api/v1/continuity/courses",
        json={
            "patient_id": "PAT-CONT-01",
            "clinical_context": "palliative_bone_brain",
            "total_fractions": 5,
            "prescribed_start_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "urgency_tier": "emergency",
            "baseline_subgroup": "subgroup_a",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    emergency_id = created.json()["id"]
    # Both machines down for the whole horizon: nothing can be treated.
    for mid in ("LINAC-01", "LINAC-02"):
        r = client.post(
            f"/api/v1/continuity/machines/{mid}/status",
            json={"status": "down", "reason": "test: beam fault"},
            headers=headers,
        )
        assert r.status_code == 200
    res = client.post("/api/v1/continuity/schedule/solve", json={"horizon_days": 7}, headers=headers)
    assert res.status_code == 200
    sol = res.json()
    assert sol["assignments"] == []
    assert any(
        emergency_id in w and "urgency bound 3 days" in w for w in sol["warnings"]
    ), sol["warnings"]


def test_urgency_ranking_promotes_flagged_course_above_higher_tier_waiting_course(client):
    """Clinician flag outranks clinical tier among waiting courses; ongoing still first."""
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"}
    created = client.post(
        "/api/v1/continuity/courses",
        json={
            "patient_id": "PAT-CONT-01",
            "clinical_context": "adjuvant_post_lumpectomy",
            "total_fractions": 15,
            "prescribed_start_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "urgency_tier": "urgent",
            "baseline_subgroup": "subgroup_a",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    new_id = created.json()["id"]
    sol = client.post("/api/v1/continuity/schedule/solve", json={}, headers=headers).json()
    rank = {a["course_id"]: a["priority_rank"] for a in sol["assignments"]}
    assert rank["RTC-002"] == 1  # ongoing course
    assert rank[new_id] == 2  # flagged lumpectomy beats routine lumpectomy RTC-001
    assert rank["RTC-001"] == 3


def test_schedule_confirm_and_delay_ledger(client):
    """Test confirming a schedule creates immutable DelayLedgerEntry records and updates courses."""
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"}

    # 1. Solve first
    solve_res = client.post(
        "/api/v1/continuity/schedule/solve",
        json={"horizon_days": 14, "fairness_disparity_bound": 5.0, "max_wait_days": 30},
        headers=headers,
    )
    sol = solve_res.json()

    # 2. Confirm schedule
    confirm_res = client.post(
        "/api/v1/continuity/schedule/confirm",
        json={
            "assignments": sol["assignments"],
            "reason": "Clinician approved slot reallocation following LINAC-02 downtime",
        },
        headers=headers,
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["confirmed"] is True
    assert confirm_data["ledger_entries_created"] >= 2
    assert confirm_data["audit_event_id"] is not None

    # 3. Query delay ledger
    ledger_res = client.get("/api/v1/continuity/ledger?patient_id=PAT-CONT-01", headers=headers)
    assert ledger_res.status_code == 200
    ledger_entries = ledger_res.json()
    assert len(ledger_entries) >= 1
    assert ledger_entries[0]["patient_id"] == "PAT-CONT-01"
    assert ledger_entries[0]["recorded_by"] in ("dr_folashade", "local_dev")


def test_patient_delay_notice_endpoint(client):
    """Test patient delay notice generation with plain-language communication."""
    headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"}

    res = client.get("/api/v1/continuity/patients/PAT-CONT-01/delay-notice", headers=headers)
    assert res.status_code == 200
    notice = res.json()
    assert notice["patient_id"] == "PAT-CONT-01"
    assert notice["has_active_treatment"] is True
    assert notice["clinical_context"] == "adjuvant_post_lumpectomy"
    assert "radiotherapy" in notice["plain_language_notice"].lower()


def test_continuity_security_and_consent_invariants(client):
    """Test that unconsented patient access is rejected with 403 and nurse cannot confirm schedule."""
    # 1. Unconsented patient cannot view delay notice
    clinician_headers = {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR-01"}
    unconsented_res = client.get(
        "/api/v1/continuity/patients/PAT-NO-CONSENT/delay-notice", headers=clinician_headers
    )
    assert unconsented_res.status_code == 403
    assert "consent" in unconsented_res.json()["detail"].lower()

    # 2. Nurse Clerk cannot confirm schedule (clinician/admin required)
    nurse_headers = {"X-Vigil-Role": "nurse_clerk", "X-Vigil-User-Id": "USR-NURSE-01"}
    confirm_res = client.post(
        "/api/v1/continuity/schedule/confirm",
        json={"assignments": [], "reason": "Nurse attempt"},
        headers=nurse_headers,
    )
    assert confirm_res.status_code == 403
