"""Comprehensive attack matrix verification for Phase 7a.

Tests all routes returning clinical content or mutating clinical/continuity state
against unauthorized roles, cross-patient callers, unconsented callers, and locked bad-news states.
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ["ENVIRONMENT"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import (
    CaregiverShare,
    ConsentRecord,
    Facility,
    LinacMachine,
    MachineStatus,
    Observation,
    Patient,
    RadiotherapyContext,
    RadiotherapyCourse,
    RiskAssessment,
    User,
    UserRole,
)


def run_attacks():
    with NamedTemporaryFile(suffix=".db") as tmp:
        db_path = tmp.name
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        # Seed Facility
        fac = Facility(id="FAC-01", name="UCH Ibadan Oncology", code="UCH-ONC", tier="tertiary")
        session.add(fac)

        # Seed Users
        dr = User(
            id="USR-DR",
            username="dr_folashade",
            email="dr@uch.edu.ng",
            role=UserRole.CLINICIAN.value,
            full_name="Dr Folashade",
            hashed_password="pw",
            facility_id=fac.id,
        )
        nurse = User(
            id="USR-NURSE",
            username="nurse_clerk",
            email="nurse@uch.edu.ng",
            role=UserRole.NURSE_CLERK.value,
            full_name="Nurse Clerk",
            hashed_password="pw",
            facility_id=fac.id,
        )
        pt1_user = User(
            id="PAT-001",
            username="PAT-001",
            email="pt1@uch.edu.ng",
            role=UserRole.PATIENT.value,
            full_name="Patient One",
            hashed_password="pw",
            facility_id=fac.id,
        )
        pt2_user = User(
            id="PAT-002",
            username="PAT-002",
            email="pt2@uch.edu.ng",
            role=UserRole.PATIENT.value,
            full_name="Patient Two",
            hashed_password="pw",
            facility_id=fac.id,
        )
        session.add_all([dr, nurse, pt1_user, pt2_user])

        # Seed Patients
        p1 = Patient(
            id="PAT-001",
            biological_sex="female",
            primary_cancer_type="breast",
            age=45,
            disclosure_unlocked_at=None,  # LOCKED
        )
        p2 = Patient(
            id="PAT-002",
            biological_sex="female",
            primary_cancer_type="cervical",
            age=52,
            disclosure_unlocked_at=now,  # UNLOCKED
        )
        p_no_consent = Patient(
            id="PAT-NOCONSENT",
            biological_sex="male",
            primary_cancer_type="prostate",
            age=60,
        )
        session.add_all([p1, p2, p_no_consent])

        # Seed Consents
        c1 = ConsentRecord(patient_id=p1.id, granted=True, scope="full", granted_at=now)
        c2 = ConsentRecord(patient_id=p2.id, granted=True, scope="full", granted_at=now)
        session.add_all([c1, c2])

        # Seed Escalated Observation & Risk on P1
        obs1 = Observation(
            id="OBS-ESC-01",
            patient_id=p1.id,
            analyte_code="ca_15_3",
            value=120.0,
            unit="U/mL",
            raw_value=120.0,
            raw_unit="U/mL",
            specimen_collected_at=now - timedelta(days=2),
            plausibility_status="plausible",
        )
        session.add(obs1)

        risk1 = RiskAssessment(
            id="RISK-ESC-01",
            patient_id=p1.id,
            observation_id=obs1.id,
            assessment_date=now - timedelta(days=1),
            model_versions={"M3": "1.0", "M5": "1.0"},
            input_hash="f" * 64,
            score=0.92,
            risk_tier="high",
            abstention=False,
            adjudicated_action="escalate",
            clinical_note="Recurrence confirmed; urgent multidisciplinary review required.",
        )
        session.add(risk1)

        # Seed Caregiver Shares (hashed tokens)
        token_p1_valid = "vigil_cg_live_valid_p1_secret_token"
        token_p1_hash = hashlib.sha256(token_p1_valid.encode("utf-8")).hexdigest()
        share_valid = CaregiverShare(
            id="SHR-001",
            patient_id=p1.id,
            caregiver_name="Amina Bello",
            relationship_type="daughter",
            token_hash=token_p1_hash,
            token_preview="vigil_cg_live...oken",
            status="active",
            scope="view_summary",
            expires_at=now + timedelta(days=30),
        )

        token_expired = "vigil_cg_live_expired_token_secret"
        share_expired = CaregiverShare(
            id="SHR-002",
            patient_id=p1.id,
            caregiver_name="Old Caregiver",
            relationship_type="sister",
            token_hash=hashlib.sha256(token_expired.encode("utf-8")).hexdigest(),
            token_preview="vigil_cg_live...cret",
            status="active",
            scope="view_summary",
            expires_at=now - timedelta(days=1),
        )

        token_revoked = "vigil_cg_live_revoked_token_secret"
        share_revoked = CaregiverShare(
            id="SHR-003",
            patient_id=p1.id,
            caregiver_name="Revoked Caregiver",
            relationship_type="brother",
            token_hash=hashlib.sha256(token_revoked.encode("utf-8")).hexdigest(),
            token_preview="vigil_cg_live...cret",
            status="revoked",
            scope="view_summary",
            expires_at=now + timedelta(days=30),
            revoked_at=now,
        )
        session.add_all([share_valid, share_expired, share_revoked])

        # Seed LINAC Machine & Course
        m1 = LinacMachine(
            id="LINAC-01",
            facility_id=fac.id,
            machine_name="LINAC-01 (Elekta)",
            daily_slot_capacity=16,
            status=MachineStatus.OPERATIONAL.value,
        )
        session.add(m1)

        rtc1 = RadiotherapyCourse(
            id="RTC-001",
            patient_id=p1.id,
            assigned_machine_id=m1.id,
            clinical_context=RadiotherapyContext.ADJUVANT_POST_LUMPECTOMY.value,
            total_fractions=15,
            fractions_delivered=0,
            prescribed_start_date=now - timedelta(days=10),
            scheduled_start_date=now - timedelta(days=3),
            urgency_tier="routine",
            status="pending",
        )
        session.add(rtc1)
        p1_id = p1.id
        p2_id = p2.id
        p_no_consent_id = p_no_consent.id
        obs1_id = obs1.id
        session.commit()

    client = TestClient(app)

    attacks = [
        {
            "name": "Patient reads locked bad-news explainer directly",
            "method": "GET",
            "url": f"/api/v1/patients/{p1_id}/observations/{obs1_id}/explainer",
            "headers": {"X-Vigil-Role": "patient", "X-Vigil-User-Id": p1_id},
            "json": None,
            "expected_status": 403,
            "match_in_body": "disclosure_locked",
        },
        {
            "name": "Caregiver reads locked bad-news explainer via share token",
            "method": "GET",
            "url": f"/api/v1/companion/share/{token_p1_valid}/observations/{obs1_id}/explainer",
            "headers": {},
            "json": None,
            "expected_status": 403,
            "match_in_body": "disclosure_locked",
        },
        {
            "name": "Caregiver summary withholds clinical risk when disclosure locked",
            "method": "GET",
            "url": f"/api/v1/companion/share/{token_p1_valid}",
            "headers": {},
            "json": None,
            "expected_status": 200,
            "custom_check": lambda r: (
                r.json()["latest_risk"] is not None
                and r.json()["latest_risk"].get("withheld") is True
            ),
        },
        {
            "name": "Caregiver summary fails with expired token",
            "method": "GET",
            "url": f"/api/v1/companion/share/{token_expired}",
            "headers": {},
            "json": None,
            "expected_status": 403,
            "match_in_body": "expired",
        },
        {
            "name": "Caregiver summary fails with revoked token",
            "method": "GET",
            "url": f"/api/v1/companion/share/{token_revoked}",
            "headers": {},
            "json": None,
            "expected_status": 403,
            "match_in_body": "revoked",
        },
        {
            "name": "Nurse clerk attempts to unlock disclosure (bad-news release)",
            "method": "POST",
            "url": f"/api/v1/patients/{p1_id}/disclosure/unlock",
            "headers": {"X-Vigil-Role": "nurse_clerk", "X-Vigil-User-Id": "USR-NURSE"},
            "json": {},
            "expected_status": 403,
            "match_in_body": "lacks permission",
        },
        {
            "name": "Nurse clerk attempts to re-lock disclosure",
            "method": "POST",
            "url": f"/api/v1/patients/{p1_id}/disclosure/lock",
            "headers": {"X-Vigil-Role": "nurse_clerk", "X-Vigil-User-Id": "USR-NURSE"},
            "json": {"reason": "Nurse attempt to lock"},
            "expected_status": 403,
            "match_in_body": "lacks permission",
        },
        {
            "name": "Unconsented patient delay notice access blocked",
            "method": "GET",
            "url": f"/api/v1/continuity/patients/{p_no_consent_id}/delay-notice",
            "headers": {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR"},
            "json": None,
            "expected_status": 403,
            "match_in_body": "consent is absent",
        },
        {
            "name": "Patient PAT-001 attempts cross-patient read of PAT-002 delay notice",
            "method": "GET",
            "url": f"/api/v1/continuity/patients/{p2_id}/delay-notice",
            "headers": {"X-Vigil-Role": "patient", "X-Vigil-User-Id": p1_id},
            "json": None,
            "expected_status": 403,
            "match_in_body": "cannot access another patient's records",
        },
        {
            "name": "Nurse clerk attempts to confirm radiotherapy schedule",
            "method": "POST",
            "url": "/api/v1/continuity/schedule/confirm",
            "headers": {"X-Vigil-Role": "nurse_clerk", "X-Vigil-User-Id": "USR-NURSE"},
            "json": {"assignments": [], "reason": "Unauthorized nurse confirmation"},
            "expected_status": 403,
            "match_in_body": "lacks permission",
        },
        {
            "name": "Nurse clerk attempts to update LINAC machine status",
            "method": "POST",
            "url": "/api/v1/continuity/machines/LINAC-01/status",
            "headers": {"X-Vigil-Role": "nurse_clerk", "X-Vigil-User-Id": "USR-NURSE"},
            "json": {"status": "down", "reason": "Unauthorized nurse update"},
            "expected_status": 403,
            "match_in_body": "lacks permission",
        },
        {
            "name": "Clinician successfully re-locks disclosure",
            "method": "POST",
            "url": f"/api/v1/patients/{p2_id}/disclosure/lock",
            "headers": {"X-Vigil-Role": "clinician", "X-Vigil-User-Id": "USR-DR"},
            "json": {"reason": "Secondary clinical review requested"},
            "expected_status": 200,
            "custom_check": lambda r: r.json()["locked"] is True,
        },
    ]

    print("=" * 80)
    print("PHASE 7A SECURITY & ACCESS CONTROL ATTACK MATRIX")
    print("=" * 80)

    all_passed = True
    results = []

    for idx, att in enumerate(attacks, 1):
        method = att["method"]
        url = att["url"]
        headers = att["headers"]
        json_data = att["json"]
        expected_status = att["expected_status"]

        if method == "GET":
            res = client.get(url, headers=headers)
        elif method == "POST":
            res = client.post(url, headers=headers, json=json_data)
        else:
            raise ValueError(f"Unknown method {method}")

        status_ok = res.status_code == expected_status
        body_text = res.text
        check_ok = True
        if "match_in_body" in att:
            check_ok = att["match_in_body"].lower() in body_text.lower()
        if "custom_check" in att and status_ok:
            check_ok = check_ok and att["custom_check"](res)

        passed = status_ok and check_ok
        if not passed:
            all_passed = False

        status_mark = "PASS" if passed else "FAIL"
        print(f"[{idx:02d}] {status_mark} | {method:4s} {url}")
        print(f"     Principal: {headers.get('X-Vigil-Role', 'Anonymous/Token')}")
        print(f"     Expected: {expected_status} | Got: {res.status_code}")
        print(f"     Body: {body_text[:120]}...")
        print("-" * 80)

        results.append(
            {
                "idx": idx,
                "name": att["name"],
                "method": method,
                "url": url,
                "principal": headers.get("X-Vigil-Role", "Anonymous/Token"),
                "expected_status": expected_status,
                "actual_status": res.status_code,
                "passed": passed,
                "body_snippet": body_text[:140],
            }
        )

    print(
        f"\nSummary: {sum(1 for r in results if r['passed'])} / {len(results)} attack tests PASSED."
    )
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_attacks()
