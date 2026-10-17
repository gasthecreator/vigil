#!/usr/bin/env python3
"""E2E Server Runner with Seeded Test Database.

Runs the real FastAPI application on http://127.0.0.1:8000 with a seeded SQLite database
for Playwright end-to-end integration tests.
Master Plan §6.9 / Condition P9-B.
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure ROOT and apps/api are on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "vigil-ml"))
sys.path.insert(0, str(ROOT / "packages" / "vigil-core"))

from cryptography.fernet import Fernet

# Generate a valid urlsafe base64 key
real_key = Fernet.generate_key().decode()
os.environ["ENVIRONMENT"] = "local"
os.environ["REQUIRE_AUTH"] = "false"
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'data' / 'e2e_workstation.db'}"
os.environ["VIGIL_FIELD_ENCRYPTION_KEYS"] = real_key
os.environ["FIELD_ENCRYPTION_KEYS"] = real_key

import uvicorn  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from vigil_api.crypto import compute_blind_index  # noqa: E402
from vigil_api.database import Base  # noqa: E402
from vigil_api.main import app  # noqa: E402
from vigil_api.models.patient import BaselineProfile, Patient  # noqa: E402
from vigil_api.models.v2 import (  # noqa: E402
    Alert,
    AlertSeverity,
    AlertStatus,
    CaregiverShare,
    ConsentRecord,
    CourseStatus,
    DelayLedgerEntry,
    FollowUpTask,
    FollowUpTaskStatus,
    FollowUpTaskType,
    LinacMachine,
    MachineStatus,
    Observation,
    RadiotherapyContext,
    RadiotherapyCourse,
    RiskAssessment,
    Symptom,
    User,
    UserRole,
)


def seed_database():
    """Initializes schema and seeds realistic clinical data for M9 workstation tests."""
    db_path = ROOT / "data" / "e2e_workstation.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        now = datetime.now(timezone.utc)

        # 1. Clinician User
        clinician = User(
            id="USR-CLINICIAN-01",
            username="dr_adebayo",
            email="adebayo@uch.edu.ng",
            hashed_password="pw",
            role=UserRole.CLINICIAN.value,
            full_name="Dr. Folashade Adebayo",
            created_at=now - timedelta(days=100),
        )
        admin = User(
            id="USR-ADMIN-01",
            username="admin_lead",
            email="admin@uch.edu.ng",
            hashed_password="pw",
            role=UserRole.ADMIN.value,
            full_name="Hospital Data Admin",
            created_at=now - timedelta(days=100),
        )
        db.add_all([clinician, admin])

        # 2. Patient PAT-001 (Consented, active surveillance, has observation history)
        p1 = Patient(
            id="PAT-001",
            age=52,
            status="active",
            mrn="MRN-UCH-2026-101",
            mrn_bidx=compute_blind_index("MRN-UCH-2026-101"),
            external_id="EXT-UCH-101",
            external_id_bidx=compute_blind_index("EXT-UCH-101"),
            synthetic=True,
            created_at=now - timedelta(days=90),
            updated_at=now,
        )
        db.add(p1)
        db.flush()

        # Consent record for PAT-001
        c1 = ConsentRecord(
            patient_id=p1.id,
            granted=True,
            scope="surveillance_monitoring",
            granted_at=now - timedelta(days=90),
        )
        db.add(c1)

        # Baseline profile for PAT-001
        bp1 = BaselineProfile(
            patient_id=p1.id,
            tumor_stage=2,
            er_status=True,
            pr_status=True,
            her2_status=False,
            has_hypertension=False,
            renal_history=False,
            target_organ_susceptibility_vector=[0.55, 0.25, 0.15, 0.05],
        )
        db.add(bp1)

        # Historical baseline observation for PAT-001 (CA 15-3 = 23.5 U/mL)
        obs0 = Observation(
            id="OBS-000",
            patient_id=p1.id,
            analyte_code="ca_15_3",
            value=23.5,
            unit="U/mL",
            raw_value=23.5,
            raw_unit="U/mL",
            specimen_collected_at=now - timedelta(days=60),
            result_received_at=now - timedelta(days=60),
            created_at=now - timedelta(days=60),
        )
        db.add(obs0)
        db.flush()

        # Initial risk assessment for PAT-001
        ra0 = RiskAssessment(
            id="RA-000",
            patient_id=p1.id,
            observation_id=obs0.id,
            assessment_date=now - timedelta(days=60),
            model_versions={"M3": "1.0", "K2": "1.0", "M5": "1.0"},
            input_hash="hash0",
            score=0.08,
            risk_tier="low",
            adjudicated_action="explained",
            clinical_note="Biomarker stable within expected biological variation.",
            created_at=now - timedelta(days=60),
        )
        db.add(ra0)
        db.flush()

        # Recent spike observation for PAT-001 (CA 15-3 = 180.0 U/mL)
        obs1 = Observation(
            id="OBS-001",
            patient_id=p1.id,
            analyte_code="ca_15_3",
            value=180.0,
            unit="U/mL",
            raw_value=180.0,
            raw_unit="U/mL",
            plausibility_status="implausible",
            specimen_collected_at=now - timedelta(days=2),
            result_received_at=now - timedelta(days=1),
            created_at=now - timedelta(days=1),
        )
        db.add(obs1)
        db.flush()

        # Risk assessment for OBS-001
        ra1 = RiskAssessment(
            id="RA-001",
            patient_id=p1.id,
            observation_id=obs1.id,
            assessment_date=now - timedelta(days=1),
            model_versions={"M3": "1.0", "M5": "1.0"},
            input_hash="hash1",
            score=0.65,
            risk_tier="moderate",
            adjudicated_action="needs_repeat",
            clinical_note="Significant elevation flagged. Repeat specimen recommended.",
            created_at=now - timedelta(days=1),
        )
        db.add(ra1)
        db.flush()

        # Seeded escalate observation for PAT-001 to test bad-news mode server gating
        obs_esc = Observation(
            id="OBS-ESC-001",
            patient_id=p1.id,
            analyte_code="ca_15_3",
            value=38.0,
            unit="U/mL",
            raw_value=38.0,
            raw_unit="U/mL",
            plausibility_status="plausible",
            specimen_collected_at=now - timedelta(hours=6),
            result_received_at=now - timedelta(hours=2),
            created_at=now - timedelta(hours=2),
        )
        db.add(obs_esc)
        db.flush()

        ra_esc = RiskAssessment(
            id="RA-ESC-001",
            patient_id=p1.id,
            observation_id=obs_esc.id,
            assessment_date=now - timedelta(hours=2),
            model_versions={"M3": "1.0", "M5": "1.0"},
            input_hash="hash_esc",
            score=0.91,
            risk_tier="high",
            adjudicated_action="escalate",
            clinical_note="Confirmed exponential kinetic progression requiring multidisciplinary care team review.",
            created_at=now - timedelta(hours=2),
        )
        db.add(ra_esc)
        db.flush()

        # Seeded symptom for PAT-001
        sym1 = Symptom(
            id="SYM-001",
            patient_id=p1.id,
            symptom_name="Fatigue",
            severity=2,
            notes="Mild fatigue after morning walks",
            input_modality="text",
            recorded_at=now - timedelta(days=2),
            created_at=now - timedelta(days=2),
        )
        db.add(sym1)

        # Seeded caregiver share for PAT-001
        raw_token = "test-caregiver-token-12345"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        token_preview = f"{raw_token[:5]}...{raw_token[-4:]}"
        share1 = CaregiverShare(
            id="CS-001",
            patient_id=p1.id,
            token_hash=token_hash,
            token_preview=token_preview,
            caregiver_name="Chinedu Adebayo",
            relationship_type="Spouse",
            scope="view_summary",
            status="active",
            expires_at=now + timedelta(days=30),
            created_at=now - timedelta(days=5),
        )
        db.add(share1)

        # Follow-Up Task for PAT-001 (Level 2 urgent task)
        task1 = FollowUpTask(
            id="TSK-001",
            patient_id=p1.id,
            task_type=FollowUpTaskType.REPEAT_SPECIMEN.value,
            status=FollowUpTaskStatus.PENDING.value,
            due_date=now + timedelta(days=2),
            escalation_level=2,
            notes="Surveillance guardian alert: repeat confirmation draw required",
            created_at=now - timedelta(days=1),
            updated_at=now,
        )
        db.add(task1)

        # Alert for PAT-001
        alt1 = Alert(
            id="ALT-PAT-001-01",
            patient_id=p1.id,
            risk_assessment_id=ra0.id,
            alert_type="surveillance_anomaly",
            severity=AlertSeverity.CRITICAL.value,
            status=AlertStatus.OPEN.value,
            trigger_reason="CA 15-3: Significant elevation exceeding RCV",
            created_at=now - timedelta(days=1),
        )
        db.add(alt1)

        # 3. Patient PAT-002 (Consented, lower risk)
        p2 = Patient(
            id="PAT-002",
            age=48,
            status="active",
            mrn="MRN-LUTH-2026-202",
            mrn_bidx=compute_blind_index("MRN-LUTH-2026-202"),
            external_id="EXT-LUTH-202",
            external_id_bidx=compute_blind_index("EXT-LUTH-202"),
            synthetic=True,
            created_at=now - timedelta(days=45),
            updated_at=now,
        )
        db.add(p2)
        db.flush()

        c2 = ConsentRecord(
            patient_id=p2.id,
            granted=True,
            scope="surveillance_monitoring",
            granted_at=now - timedelta(days=45),
        )
        db.add(c2)

        bp2 = BaselineProfile(
            patient_id=p2.id,
            tumor_stage=1,
            er_status=True,
            pr_status=False,
            her2_status=False,
            has_hypertension=False,
            renal_history=False,
            target_organ_susceptibility_vector=[0.70, 0.15, 0.10, 0.05],
        )
        db.add(bp2)

        task2 = FollowUpTask(
            id="TSK-002",
            patient_id=p2.id,
            task_type=FollowUpTaskType.CLINICAL_REVIEW.value,
            status=FollowUpTaskStatus.IN_PROGRESS.value,
            due_date=now + timedelta(days=14),
            escalation_level=0,
            notes="Routine quarterly follow-up",
            created_at=now - timedelta(days=5),
            updated_at=now,
        )
        db.add(task2)

        # 4. Patient PAT-NOCONSENT-99 (Registered, NO consent on record, to verify 403)
        p3 = Patient(
            id="PAT-NOCONSENT-99",
            age=60,
            status="active",
            mrn="MRN-UNCONSENTED-99",
            mrn_bidx=compute_blind_index("MRN-UNCONSENTED-99"),
            external_id="EXT-UNCONSENTED-99",
            external_id_bidx=compute_blind_index("EXT-UNCONSENTED-99"),
            synthetic=True,
            created_at=now - timedelta(days=10),
            updated_at=now,
        )
        db.add(p3)

        # 5. LINAC Machines (M7 Treatment Continuity)
        linac1 = LinacMachine(
            id="LINAC-01",
            machine_name="LINAC-01 (Elekta Synergy)",
            daily_slot_capacity=16,
            status=MachineStatus.OPERATIONAL.value,
            downtime_started_at=None,
            expected_return_at=None,
            created_at=now - timedelta(days=180),
            updated_at=now,
        )
        linac2 = LinacMachine(
            id="LINAC-02",
            machine_name="LINAC-02 (Varian Clinac)",
            daily_slot_capacity=16,
            status=MachineStatus.DOWN.value,
            downtime_started_at=now - timedelta(days=2),
            expected_return_at=now + timedelta(days=5),
            created_at=now - timedelta(days=180),
            updated_at=now,
        )
        db.add_all([linac1, linac2])

        # 6. Radiotherapy Courses (M7)
        rtc1 = RadiotherapyCourse(
            id="RTC-001",
            patient_id=p1.id,
            assigned_machine_id=linac1.id,
            clinical_context=RadiotherapyContext.ADJUVANT_POST_LUMPECTOMY.value,
            total_fractions=15,
            fractions_delivered=0,
            prescribed_start_date=now - timedelta(days=14),
            scheduled_start_date=now - timedelta(days=7),
            urgency_tier="routine",
            status=CourseStatus.PENDING.value,
            baseline_subgroup="public_referral",
            created_at=now - timedelta(days=14),
            updated_at=now,
        )
        rtc2 = RadiotherapyCourse(
            id="RTC-002",
            patient_id=p2.id,
            assigned_machine_id=linac2.id,
            clinical_context=RadiotherapyContext.CURATIVE_TNBC.value,
            total_fractions=25,
            fractions_delivered=5,
            prescribed_start_date=now - timedelta(days=21),
            scheduled_start_date=now - timedelta(days=3),
            urgency_tier="urgent",
            status=CourseStatus.IN_PROGRESS.value,
            baseline_subgroup="direct_intake",
            created_at=now - timedelta(days=21),
            updated_at=now,
        )
        db.add_all([rtc1, rtc2])

        # 7. Delay Ledger Entry for RTC-001 (documenting initial delay)
        ledger1 = DelayLedgerEntry(
            id="LEDGER-001",
            patient_id=p1.id,
            course_id=rtc1.id,
            delay_days=7,
            reason="Capacity re-allocation following LINAC-02 unscheduled maintenance",
            marginal_harm=0.0175,
            moved_from_date=now - timedelta(days=14),
            moved_to_date=now - timedelta(days=7),
            clinician_overridden=False,
            recorded_by="system_cp_sat",
            created_at=now - timedelta(days=7),
        )
        db.add(ledger1)

        db.commit()
        print(f"✅ Seeded E2E database with 3 patients, 2 LINACs, and 2 RT courses at {db_path}")
    finally:
        db.close()


def main():
    seed_database()
    print("🚀 Starting FastAPI E2E server on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
