"""API and Security Attack Tests for Family & Patient Companion (M8).

Verifies Master Plan §6.8, §10, §11, and Phase 6b:
1. Plain-language result explainer driven by M3 verdicts and M5 engine.
2. Second-Look Request creating FollowUpTask with DB verification and audit checks.
3. Bad-news mode gated disclosure unlock and audit tracking.
4. Symptom diary logging (text + speech modality) and listing with consent checks.
5. Scoped, revocable, audited caregiver sharing with adversarial attack matrix:
   - Invalid token -> 404 Not Found
   - Revoked token -> 403 Forbidden
   - Expired token -> 403 Forbidden
   - Patient consent withdrawn -> 403 Forbidden
   - Scope enforcement ('view_summary' vs 'full_history')
   - Delegated caregiver symptom logging
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from vigil_api.auth import create_access_token
from vigil_api.crypto import compute_blind_index
from vigil_api.database import Base, get_db
from vigil_api.main import app
from vigil_api.models.v2 import (
    AuditEvent,
    CaregiverShare,
    ConsentRecord,
    Facility,
    FollowUpTask,
    Observation,
    Patient,
    RiskAssessment,
    UserRole,
)


@pytest.fixture
def companion_env(tmp_path):
    """Set up an isolated SQLite test database with seeded facility and patient."""
    db_file = tmp_path / "test_companion.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        # Facility
        fac = Facility(
            id="fac-onc-01",
            name="Lagos Oncology Centre",
            code="LOC-01",
            country="NG",
            tier="tertiary",
            active=True,
            created_at=now,
        )
        session.add(fac)

        # Consented Patient
        p1 = Patient(
            id="pat-comp-01",
            facility_id="fac-onc-01",
            mrn="MRN-COMP-01",
            mrn_bidx=compute_blind_index("MRN-COMP-01"),
            age=48,
            biological_sex="female",
            primary_cancer_type="breast",
            synthetic=True,
            status="active",
            created_at=now,
            updated_at=now,
        )
        session.add(p1)

        # Active consent
        session.add(
            ConsentRecord(
                patient_id="pat-comp-01",
                consent_type="surveillance_monitoring",
                granted=True,
                granted_at=now,
                scope="full",
            )
        )

        # Historical observations (4 historical + 1 recent spike)
        obs1 = Observation(
            id="obs-comp-01",
            patient_id="pat-comp-01",
            analyte_code="ca_15_3",
            value=18.0,
            unit="U/mL",
            raw_value=18.0,
            raw_unit="U/mL",
            specimen_collected_at=now - timedelta(days=90),
            plausibility_status="plausible",
        )
        obs2 = Observation(
            id="obs-comp-02",
            patient_id="pat-comp-01",
            analyte_code="ca_15_3",
            value=18.5,
            unit="U/mL",
            raw_value=18.5,
            raw_unit="U/mL",
            specimen_collected_at=now - timedelta(days=60),
            plausibility_status="plausible",
        )
        obs3 = Observation(
            id="obs-comp-03",
            patient_id="pat-comp-01",
            analyte_code="ca_15_3",
            value=19.0,
            unit="U/mL",
            raw_value=19.0,
            raw_unit="U/mL",
            specimen_collected_at=now - timedelta(days=30),
            plausibility_status="plausible",
        )
        obs_spike = Observation(
            id="obs-comp-spike",
            patient_id="pat-comp-01",
            analyte_code="ca_15_3",
            value=180.0,
            unit="U/mL",
            raw_value=180.0,
            raw_unit="U/mL",
            specimen_collected_at=now - timedelta(days=2),
            plausibility_status="implausible",
        )
        session.add_all([obs1, obs2, obs3, obs_spike])

        # Risk assessment
        risk = RiskAssessment(
            id="risk-comp-01",
            patient_id="pat-comp-01",
            assessment_date=now - timedelta(days=2),
            model_versions={"M3": "1.0", "M5": "1.0"},
            input_hash="a" * 64,
            score=0.88,
            risk_tier="high",
            abstention=False,
            adjudicated_action="needs_repeat",
            clinical_note="The recommended clinical action is needs_repeat.",
            created_at=now,
        )
        session.add(risk)
        session.commit()

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()


def get_token_headers(
    user_id: str, role: UserRole, patient_id: Optional[str] = None
) -> Dict[str, str]:
    token = create_access_token(
        subject=user_id,
        role=role.value,
        patient_id=patient_id,
        expires_delta=timedelta(hours=1),
    )
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# 1. Symptom Diary Tests (Text & Speech Modality)
# =========================================================================


def test_symptom_diary_crud_and_consent(companion_env):
    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    patient_id = "pat-comp-01"

    # Record symptom via text
    resp_text = client.post(
        f"/api/v1/patients/{patient_id}/symptoms",
        headers=clinician_hdr,
        json={
            "symptom_name": "bone_pain",
            "severity": 2,
            "notes": "Mild lower back pain on waking up",
            "input_modality": "text",
        },
    )
    assert resp_text.status_code == 201
    data_text = resp_text.json()
    assert data_text["symptom_name"] == "bone_pain"
    assert data_text["severity"] == 2
    assert data_text["input_modality"] == "text"
    assert data_text["synthetic"] is True

    # Record symptom via speech modality (voice recording input)
    resp_voice = client.post(
        f"/api/v1/patients/{patient_id}/symptoms",
        headers=clinician_hdr,
        json={
            "symptom_name": "fatigue",
            "severity": 3,
            "notes": "Transcribed voice note: Feeling very tired after short walk",
            "input_modality": "speech",
        },
    )
    assert resp_voice.status_code == 201
    assert resp_voice.json()["input_modality"] == "speech"

    # List symptoms
    resp_list = client.get(f"/api/v1/patients/{patient_id}/symptoms", headers=clinician_hdr)
    assert resp_list.status_code == 200
    symptoms = resp_list.json()
    assert len(symptoms) == 2

    # Withdraw patient consent over HTTP and verify symptoms are protected (403)
    resp_withdraw = client.post(
        f"/api/v1/patients/{patient_id}/consent",
        json={"consent_type": "surveillance_monitoring", "granted": False, "scope": "full"},
        headers=clinician_hdr,
    )
    assert resp_withdraw.status_code == 201

    resp_withdrawn = client.get(f"/api/v1/patients/{patient_id}/symptoms", headers=clinician_hdr)
    assert resp_withdrawn.status_code == 403


# =========================================================================
# 2. Caregiver Sharing Lifecycle & Scopes
# =========================================================================


def test_caregiver_share_lifecycle_and_scope(companion_env):
    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    patient_id = "pat-comp-01"

    # 1. Create caregiver share token with 'view_summary' scope
    resp_share = client.post(
        f"/api/v1/patients/{patient_id}/shares",
        headers=clinician_hdr,
        json={
            "caregiver_name": "Amina Bello",
            "relationship_type": "daughter",
            "scope": "view_summary",
            "duration_days": 14,
        },
    )
    assert resp_share.status_code == 201
    share_data = resp_share.json()
    share_token = share_data["share_token"]
    share_id = share_data["id"]
    assert share_token.startswith("cg_")
    assert share_data["status"] == "active"

    # 2. Access via caregiver token
    resp_cg = client.get(f"/api/v1/companion/share/{share_token}")
    assert resp_cg.status_code == 200
    cg_view = resp_cg.json()
    assert cg_view["caregiver_name"] == "Amina Bello"
    assert cg_view["patient"]["id"] == patient_id
    # Bad-news mode: escalate-level assessment is withheld from caregivers until a clinician releases it
    assert cg_view["latest_risk"] == {
        "withheld": True,
        "message": cg_view["latest_risk"]["message"],
    }
    assert all(o["plausibility_status"] is None for o in cg_view["observations"])
    unlock = client.post(
        f"/api/v1/patients/{patient_id}/disclosure/unlock",
        json={"reason": "clinician release"},
        headers={"X-Vigil-Role": "clinician"},
    )
    assert unlock.status_code == 200
    cg_view = client.get(f"/api/v1/companion/share/{share_token}").json()
    assert cg_view["latest_risk"]["risk_tier"] == "high"
    # Under 'view_summary', observations are capped at 3
    assert len(cg_view["observations"]) <= 3

    # 3. Caregiver records symptom on behalf of patient
    resp_cg_symp = client.post(
        f"/api/v1/companion/share/{share_token}/symptoms",
        json={
            "symptom_name": "nausea",
            "severity": 1,
            "notes": "Mild nausea reported by mother",
            "input_modality": "text",
        },
    )
    assert resp_cg_symp.status_code == 201
    assert resp_cg_symp.json()["symptom_name"] == "nausea"

    # Provenance for the explainer follows the source patient's data, not a default label.
    with Session(engine) as s:
        patient = s.get(Patient, patient_id)
        assert patient is not None
        patient.synthetic = False
        s.commit()

    # 4. Caregiver accesses plain-language observation explainer
    resp_cg_exp = client.get(
        f"/api/v1/companion/share/{share_token}/observations/obs-comp-spike/explainer"
    )
    assert resp_cg_exp.status_code == 200
    exp = resp_cg_exp.json()
    assert exp["verdict"] == "needs_repeat"
    assert exp["synthetic"] is False
    assert exp["flesch_kincaid_grade_level"] <= 8.0
    assert len(exp["questions_to_ask_your_doctor"]) == 3

    # 5. Revoke caregiver share
    resp_rev = client.delete(
        f"/api/v1/patients/{patient_id}/shares/{share_id}",
        headers=clinician_hdr,
    )
    assert resp_rev.status_code == 200
    assert resp_rev.json()["status"] == "revoked"

    # 6. Verify subsequent access by revoked token is rejected with 403
    resp_cg_after = client.get(f"/api/v1/companion/share/{share_token}")
    assert resp_cg_after.status_code == 403
    assert "revoked" in resp_cg_after.json()["detail"].lower()


# =========================================================================
# 3. Adversarial Security Attack Matrix on Companion Endpoints
# =========================================================================


def test_caregiver_share_security_attacks(companion_env):
    """Rigorous attack matrix testing invalid, expired, revoked, and unconsented tokens."""
    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    patient_id = "pat-comp-01"

    # Attack 1: Non-existent / fabricated token -> 404 Not Found
    resp_fake = client.get("/api/v1/companion/share/cg_completely_fabricated_token_12345")
    assert resp_fake.status_code == 404

    # Create active share for further attack variants
    resp_share = client.post(
        f"/api/v1/patients/{patient_id}/shares",
        headers=clinician_hdr,
        json={
            "caregiver_name": "Test Caregiver",
            "relationship_type": "spouse",
            "scope": "full_history",
            "duration_days": 1,
        },
    )
    token = resp_share.json()["share_token"]
    share_id = resp_share.json()["id"]

    # Attack 2: Expired token -> 403 Forbidden
    with Session(engine) as s:
        s.execute(
            CaregiverShare.__table__.update()
            .where(CaregiverShare.id == share_id)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        )
        s.commit()

    resp_expired = client.get(f"/api/v1/companion/share/{token}")
    assert resp_expired.status_code == 403
    assert "expired" in resp_expired.json()["detail"].lower()

    # Re-activate token and attack with patient consent withdrawal
    with Session(engine) as s:
        s.execute(
            CaregiverShare.__table__.update()
            .where(CaregiverShare.id == share_id)
            .values(expires_at=datetime.now(timezone.utc) + timedelta(days=10))
        )
        s.commit()

    # Withdraw patient consent over HTTP
    resp_withdraw = client.post(
        f"/api/v1/patients/{patient_id}/consent",
        json={"consent_type": "surveillance_monitoring", "granted": False, "scope": "full"},
        headers=clinician_hdr,
    )
    assert resp_withdraw.status_code == 201

    # Attack 3: Patient has withdrawn consent -> caregiver access rejected with 403
    resp_no_consent = client.get(f"/api/v1/companion/share/{token}")
    assert resp_no_consent.status_code == 403
    assert "consent" in resp_no_consent.json()["detail"].lower()

    # Attack 4: Proxy symptom recording without patient consent -> 403 Forbidden
    resp_symp_no_consent = client.post(
        f"/api/v1/companion/share/{token}/symptoms",
        json={"symptom_name": "cough", "severity": 2, "input_modality": "text"},
    )
    assert resp_symp_no_consent.status_code == 403


# =========================================================================
# 4. Second-Look Request and FollowUpTask Creation
# =========================================================================


def test_second_look_request_flow(companion_env):
    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    patient_id = "pat-comp-01"

    # Submit second-look request for the spike observation
    resp_sl = client.post(
        f"/api/v1/patients/{patient_id}/second-look",
        headers=clinician_hdr,
        json={
            "observation_id": "obs-comp-spike",
            "reason": "10x sudden jump from 18 to 180 U/mL",
            "notes": "Patient family requesting repeat test confirmation before imaging",
        },
    )
    assert resp_sl.status_code == 201
    sl_data = resp_sl.json()
    assert sl_data["observation_id"] == "obs-comp-spike"
    assert sl_data["analyte_code"] == "ca_15_3"
    assert sl_data["status"] == "submitted"

    # Verify that a FollowUpTask was persisted in the database
    with Session(engine) as s:
        task = s.execute(
            select(FollowUpTask).where(
                FollowUpTask.id == sl_data["task_id"],
                FollowUpTask.patient_id == patient_id,
            )
        ).scalar_one_or_none()
        assert task is not None
        assert task.task_type == "second_look_request"
        assert task.status == "pending"

        # Verify audit trail
        audit = s.execute(
            select(AuditEvent).where(
                AuditEvent.action == "patient.second_look_requested",
                AuditEvent.resource_id == sl_data["task_id"],
            )
        ).scalar_one_or_none()
        assert audit is not None
        assert audit.details["observation_id"] == "obs-comp-spike"


# =========================================================================
# 5. Bad-News Mode Gated Disclosure Unlock
# =========================================================================


def test_bad_news_mode_disclosure_unlock(companion_env):
    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    patient_id = "pat-comp-01"

    resp_unlock = client.post(
        f"/api/v1/patients/{patient_id}/disclosure/unlock",
        headers=clinician_hdr,
        json={"reason": "patient_opt_in_reveal"},
    )
    assert resp_unlock.status_code == 200
    data = resp_unlock.json()
    assert data["unlocked"] is True
    assert data["synthetic"] is True

    # Verify audit event in DB
    with Session(engine) as s:
        audit = s.execute(
            select(AuditEvent).where(
                AuditEvent.action == "disclosure.unlocked",
                AuditEvent.resource_id == patient_id,
            )
        ).scalar_one_or_none()
        assert audit is not None
        assert audit.details["reason"] == "patient_opt_in_reveal"


# =========================================================================
# 6. Plain-Language Result Explainer Endpoint
# =========================================================================


def test_patient_observation_explainer_endpoint(companion_env):
    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    patient_id = "pat-comp-01"

    with Session(engine) as s:
        patient = s.get(Patient, patient_id)
        assert patient is not None
        patient.synthetic = False
        s.commit()

    # Explainer for spike observation (adjudicated as needs_repeat)
    resp = client.get(
        f"/api/v1/patients/{patient_id}/observations/obs-comp-spike/explainer",
        headers=clinician_hdr,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["observation_id"] == "obs-comp-spike"
    assert data["patient_id"] == patient_id
    assert data["analyte_code"] == "ca_15_3"
    assert data["verdict"] == "needs_repeat"
    assert "uncertainty" in data["verbal_band"].lower() or "repeat" in data["verbal_band"].lower()
    assert data["flesch_kincaid_grade_level"] <= 8.0
    assert data["word_count"] <= 120
    assert len(data["questions_to_ask_your_doctor"]) == 3
    assert data["verified"] is True
    assert data["synthetic"] is False

    # Audit check
    with Session(engine) as s:
        audit = s.execute(
            select(AuditEvent).where(
                AuditEvent.action == "observation.explainer_read",
                AuditEvent.resource_id == "obs-comp-spike",
            )
        ).scalar_one_or_none()
        assert audit is not None


# =========================================================================
# 7. Remediations: P11-E (Token Hashing), P11-A (Request-Release & Re-Lock), P11-F (Clinical Gate)
# =========================================================================


def test_caregiver_token_hashing_at_rest_and_preview_p11_e(companion_env):
    """P11-E: Bearer tokens hashed at rest; raw token returned once; list returns preview only."""
    import hashlib

    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    patient_id = "pat-comp-01"

    # 1. Create a share
    create_resp = client.post(
        f"/api/v1/patients/{patient_id}/shares",
        json={
            "caregiver_name": "Fatima Bello",
            "relationship_type": "Sister",
            "scope": "view_summary",
            "expires_in_days": 14,
        },
        headers=clinician_hdr,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    raw_token = created_data["share_token"]
    token_preview = created_data["token_preview"]
    share_id = created_data["id"]

    assert raw_token is not None
    assert raw_token.startswith("cg_")
    assert token_preview == f"{raw_token[:5]}...{raw_token[-4:]}"

    # 2. Verify database stores hash and preview, NOT plaintext token
    with Session(engine) as s:
        db_share = s.execute(
            select(CaregiverShare).where(CaregiverShare.id == share_id)
        ).scalar_one()
        assert not hasattr(db_share, "share_token")
        assert db_share.token_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        assert db_share.token_preview == token_preview

    # 3. Verify list endpoint NEVER exposes raw token
    list_resp = client.get(f"/api/v1/patients/{patient_id}/shares", headers=clinician_hdr)
    assert list_resp.status_code == 200
    shares = list_resp.json()
    matching = [sh for sh in shares if sh["id"] == share_id][0]
    assert matching["share_token"] is None
    assert matching["token_preview"] == token_preview

    # 4. Bearer token works for companion access
    comp_resp = client.get(f"/api/v1/companion/share/{raw_token}")
    assert comp_resp.status_code == 200
    assert comp_resp.json()["caregiver_name"] == "Fatima Bello"

    # 5. Attacker presenting the hash directly cannot authenticate
    hash_resp = client.get(f"/api/v1/companion/share/{db_share.token_hash}")
    assert hash_resp.status_code == 404


def test_bad_news_disclosure_request_release_and_relock_p11_a(companion_env):
    """P11-A: Patient/caregiver request-release, clinician unlock, clinician re-lock."""
    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    nurse_hdr = get_token_headers("nurse-01", UserRole.NURSE_CLERK)
    patient_id = "pat-comp-01"
    patient_hdr = get_token_headers(patient_id, UserRole.PATIENT)
    other_patient_hdr = get_token_headers("pat-other-999", UserRole.PATIENT)

    # 0. Cross-patient attack: unauthorized patient cannot request release for another
    cross_resp = client.post(
        f"/api/v1/patients/{patient_id}/disclosure/request-release",
        json={"reason": "Attacker trying to poke other patient"},
        headers=other_patient_hdr,
    )
    assert cross_resp.status_code == 403

    # 1. Patient requests clinician release
    req_resp = client.post(
        f"/api/v1/patients/{patient_id}/disclosure/request-release",
        json={
            "reason": "I am feeling ready to review my complete diagnostic findings with family."
        },
        headers=patient_hdr,
    )
    assert req_resp.status_code == 201
    task_id = req_resp.json()["task_id"]

    # Verify FollowUpTask in DB
    with Session(engine) as s:
        task = s.execute(select(FollowUpTask).where(FollowUpTask.id == task_id)).scalar_one()
        assert task.task_type == "disclosure_release_request"
        assert task.status == "pending"
        audit = s.execute(
            select(AuditEvent).where(
                AuditEvent.action == "disclosure.release_requested",
                AuditEvent.resource_id == task_id,
            )
        ).scalar_one()
        assert audit is not None

    # 2. Caregiver proxy request release
    share_resp = client.post(
        f"/api/v1/patients/{patient_id}/shares",
        json={"caregiver_name": "Tunde", "scope": "full_history", "expires_in_days": 7},
        headers=clinician_hdr,
    )
    cg_token = share_resp.json()["share_token"]
    cg_req_resp = client.post(
        f"/api/v1/companion/share/{cg_token}/disclosure/request-release",
        json={"reason": "Family gathering tomorrow, requesting clinician unlock."},
    )
    assert cg_req_resp.status_code == 201

    # 3. Non-clinician unlock rejected
    nurse_unlock = client.post(
        f"/api/v1/patients/{patient_id}/disclosure/unlock",
        json={"reason": "nurse attempt"},
        headers=nurse_hdr,
    )
    assert nurse_unlock.status_code in (401, 403)

    # 4. Clinician unlock succeeds
    clin_unlock = client.post(
        f"/api/v1/patients/{patient_id}/disclosure/unlock",
        json={"reason": "Clinician post-counseling release"},
        headers=clinician_hdr,
    )
    assert clin_unlock.status_code == 200

    with Session(engine) as s:
        p = s.execute(select(Patient).where(Patient.id == patient_id)).scalar_one()
        assert p.disclosure_unlocked_at is not None

    # 5. Clinician re-locks disclosure
    nurse_lock = client.post(
        f"/api/v1/patients/{patient_id}/disclosure/lock",
        json={"reason": "nurse lock attempt"},
        headers=nurse_hdr,
    )
    assert nurse_lock.status_code in (401, 403)

    clin_lock = client.post(
        f"/api/v1/patients/{patient_id}/disclosure/lock",
        json={"reason": "Clinician re-locking after new high-risk observation entered"},
        headers=clinician_hdr,
    )
    assert clin_lock.status_code == 200
    assert clin_lock.json()["locked"] is True

    with Session(engine) as s:
        p = s.execute(select(Patient).where(Patient.id == patient_id)).scalar_one()
        assert p.disclosure_unlocked_at is None
        lock_audit = s.execute(
            select(AuditEvent).where(
                AuditEvent.action == "disclosure.locked",
                AuditEvent.resource_id == patient_id,
            )
        ).scalar_one()
        assert lock_audit is not None


def test_bad_news_disclosure_invariant_on_all_clinical_routes_p11_f(companion_env):
    """P11-F: Assert every route returning clinical content respects disclosure state."""
    client, engine = companion_env
    clinician_hdr = get_token_headers("doc-01", UserRole.CLINICIAN)
    patient_id = "pat-comp-01"

    # Setup: ensure disclosure is locked
    with Session(engine) as s:
        p = s.execute(select(Patient).where(Patient.id == patient_id)).scalar_one()
        p.disclosure_unlocked_at = None
        s.commit()

    # Create an escalate observation
    obs_resp = client.post(
        f"/api/v1/patients/{patient_id}/observations",
        json={
            "analyte_code": "ca_15_3",
            "value": 58.0,
            "unit": "U/mL",
            "specimen_collected_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=clinician_hdr,
    )
    assert obs_resp.status_code == 201
    esc_obs_id = obs_resp.json()["observation_id"]

    # Create caregiver share
    share_resp = client.post(
        f"/api/v1/patients/{patient_id}/shares",
        json={"caregiver_name": "Uncle", "scope": "full_history", "expires_in_days": 7},
        headers=clinician_hdr,
    )
    tok = share_resp.json()["share_token"]

    # 1. Patient explainer route MUST withhold
    pat_exp = client.get(
        f"/api/v1/patients/{patient_id}/observations/{esc_obs_id}/explainer",
        headers=clinician_hdr,
    )
    assert pat_exp.status_code == 403
    assert pat_exp.json()["detail"]["code"] == "disclosure_locked"

    # 2. Caregiver explainer route MUST withhold
    cg_exp = client.get(f"/api/v1/companion/share/{tok}/observations/{esc_obs_id}/explainer")
    assert cg_exp.status_code == 403
    assert cg_exp.json()["detail"]["code"] == "disclosure_locked"

    # 3. Caregiver summary MUST withhold escalate interpretation
    cg_sum = client.get(f"/api/v1/companion/share/{tok}")
    assert cg_sum.status_code == 200
    data = cg_sum.json()
    assert data["latest_risk"]["withheld"] is True
    assert "score" not in data["latest_risk"]

    # Now unlock as clinician
    client.post(
        f"/api/v1/patients/{patient_id}/disclosure/unlock",
        json={"reason": "counseled"},
        headers=clinician_hdr,
    )

    # Both explainer routes now return full content
    assert (
        client.get(
            f"/api/v1/patients/{patient_id}/observations/{esc_obs_id}/explainer",
            headers=clinician_hdr,
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/companion/share/{tok}/observations/{esc_obs_id}/explainer").status_code
        == 200
    )
    cg_sum_unlocked = client.get(f"/api/v1/companion/share/{tok}").json()
    assert cg_sum_unlocked["latest_risk"].get("withheld") is not True
    assert "score" in cg_sum_unlocked["latest_risk"]
