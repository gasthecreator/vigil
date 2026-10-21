"""Migration tests on a populated database with upgrade/downgrade cycles and check constraint verification."""

import os
import tempfile
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from vigil_api.models.v2 import (
    Alert,
    AlertAcknowledgement,
    AlertDisposition,
    AlertSeverity,
    AlertStatus,
    AuditEvent,
    BaselineProfile,
    ConsentRecord,
    Facility,
    FollowUpTask,
    FollowUpTaskStatus,
    FollowUpTaskType,
    Observation,
    Patient,
    RiskAssessment,
    User,
    UserRole,
    calculate_audit_hash,
)


@pytest.fixture
def temp_db_alembic():
    """Create a temporary SQLite database and Alembic Config pointing to it."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db_url = f"sqlite:///{db_path}"

    # Locate alembic.ini relative to this test file
    ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # Store test url in os.environ for env.py fallback
    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url

    yield alembic_cfg, db_url

    # Cleanup
    if old_db_url is not None:
        os.environ["DATABASE_URL"] = old_db_url
    else:
        os.environ.pop("DATABASE_URL", None)

    if os.path.exists(db_path):
        os.remove(db_path)


def test_migration_lifecycle_and_constraints(temp_db_alembic):
    """Test upgrade -> populate -> check constraints -> downgrade -> upgrade cycle."""
    alembic_cfg, db_url = temp_db_alembic
    engine = create_engine(db_url)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # The retracted M1 prior is optional for new records; existing JSON values
    # are retained by the migration rather than backfilled or rewritten.
    with engine.connect() as conn:
        columns = conn.execute(text("PRAGMA table_info(baseline_profiles)")).mappings().all()
    vector_column = next(
        column for column in columns if column["name"] == "target_organ_susceptibility_vector"
    )
    assert vector_column["notnull"] == 0

    now = datetime.now(timezone.utc)

    # 2. Populate test data
    with Session(engine) as session:
        facility = Facility(
            id="fac-001",
            name="Lagos University Teaching Hospital",
            code="LUTH-NG",
            country="NG",
            tier="tertiary",
            active=True,
            created_at=now,
        )
        session.add(facility)

        user = User(
            id="usr-001",
            username="dr_adewale",
            email="adewale@luth.edu.ng",
            full_name="Dr. Funke Adewale",
            role=UserRole.CLINICIAN.value,
            facility_id="fac-001",
            active=True,
            hashed_password="mock_hashed_pw",
            created_at=now,
        )
        session.add(user)

        patient = Patient(
            id="pat-001",
            facility_id="fac-001",
            mrn="MRN-2026-001",
            age=48,
            biological_sex="female",
            primary_cancer_type="breast",
            synthetic=True,
            status="active",
            created_at=now,
            updated_at=now,
        )
        session.add(patient)

        consent = ConsentRecord(
            id="con-001",
            patient_id="pat-001",
            consent_type="surveillance_monitoring",
            granted=True,
            granted_at=now,
            scope="full",
        )
        session.add(consent)

        obs = Observation(
            id="obs-001",
            patient_id="pat-001",
            analyte_code="CA_15_3",
            value=32.4,
            unit="U/mL",
            specimen_collected_at=now,
            result_received_at=now,
            laboratory_id="LAB-LUTH-01",
            plausibility_status="valid_normal",
            raw_value=32.4,
            raw_unit="U/mL",
            status="valid",
            created_at=now,
        )
        session.add(obs)

        risk = RiskAssessment(
            id="risk-001",
            patient_id="pat-001",
            observation_id="obs-001",
            assessment_date=now,
            model_versions={"M3": "1.0", "K2": "1.0", "M5": "1.0"},
            input_hash="a" * 64,
            score=0.15,
            risk_tier="low",
            uncertainty={"credible_interval": [0.10, 0.22]},
            abstention=False,
            adjudicated_action="explained",
            clinical_note="Biomarker stable.",
            created_at=now,
        )
        session.add(risk)

        alert = Alert(
            id="alt-001",
            patient_id="pat-001",
            risk_assessment_id="risk-001",
            alert_type="biomarker_spike",
            severity=AlertSeverity.WARNING.value,
            trigger_reason="CA 15-3 crossed threshold",
            status=AlertStatus.OPEN.value,
            created_at=now,
        )
        session.add(alert)

        ack = AlertAcknowledgement(
            id="ack-001",
            alert_id="alt-001",
            user_id="usr-001",
            disposition=AlertDisposition.SAMPLE_REDRAW_ORDERED.value,
            rationale_text="Redraw ordered to rule out gross pre-analytical error.",
            acknowledged_at=now,
        )
        session.add(ack)

        task = FollowUpTask(
            id="tsk-001",
            patient_id="pat-001",
            alert_id="alt-001",
            task_type=FollowUpTaskType.REPEAT_SPECIMEN.value,
            status=FollowUpTaskStatus.PENDING.value,
            due_date=now,
            escalation_level=0,
            created_at=now,
            updated_at=now,
        )
        session.add(task)

        audit_hash = calculate_audit_hash(
            prev_hash="0" * 64,
            timestamp=now,
            actor_id="usr-001",
            actor_role=UserRole.CLINICIAN.value,
            action="observation.create",
            resource_type="observation",
            resource_id="obs-001",
            details={"value": 32.4},
        )
        audit = AuditEvent(
            id="aud-001",
            timestamp=now,
            actor_id="usr-001",
            actor_role=UserRole.CLINICIAN.value,
            action="observation.create",
            resource_type="observation",
            resource_id="obs-001",
            details={"value": 32.4},
            prev_hash="0" * 64,
            curr_hash=audit_hash,
        )
        session.add(audit)
        session.commit()

    # 3. Verify populated records exist
    with Session(engine) as session:
        pts = session.execute(select(Patient)).scalars().all()
        assert len(pts) == 1
        assert pts[0].id == "pat-001"
        assert pts[0].synthetic is True

    # 4. Check constraint test: No-Dismissal Invariant
    # A) Observation status != 'dismissed'
    with pytest.raises(IntegrityError):
        with Session(engine) as session:
            bad_obs = Observation(
                id="obs-bad",
                patient_id="pat-001",
                analyte_code="CA_15_3",
                value=50.0,
                unit="U/mL",
                specimen_collected_at=now,
                result_received_at=now,
                plausibility_status="dismissed",
                raw_value=50.0,
                raw_unit="U/mL",
                status="dismissed",  # VIOLATION of chk_observation_no_dismissal
                created_at=now,
            )
            session.add(bad_obs)
            session.commit()

    # B) RiskAssessment adjudicated_action != 'dismissed'
    with pytest.raises(IntegrityError):
        with Session(engine) as session:
            bad_risk = RiskAssessment(
                id="risk-bad",
                patient_id="pat-001",
                assessment_date=now,
                model_versions={"M3": "1.0"},
                input_hash="b" * 64,
                score=0.9,
                risk_tier="high",
                abstention=False,
                adjudicated_action="dismissed",  # VIOLATION of chk_risk_no_dismissal
                created_at=now,
            )
            session.add(bad_risk)
            session.commit()

    # 5. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # Verify tables dropped
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='patients'")
        ).scalar()
        assert result is None

    # 6. Upgrade back to head
    command.upgrade(alembic_cfg, "head")

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='patients'")
        ).scalar()
        assert result == "patients"


def test_null_m3_score_requires_abstention_and_cannot_be_downgraded(temp_db_alembic):
    alembic_cfg, db_url = temp_db_alembic
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(db_url)
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add(
            Facility(
                id="fac-abstain", name="Test", code="TEST", country="NG",
                tier="tertiary", active=True, created_at=now,
            )
        )
        session.add(
            Patient(
                id="pat-abstain", facility_id="fac-abstain", mrn="MRN-ABSTAIN",
                biological_sex="female", primary_cancer_type="breast", synthetic=True,
                status="active", created_at=now, updated_at=now,
            )
        )
        session.commit()

    with pytest.raises(IntegrityError):
        with Session(engine) as session:
            session.add(
                RiskAssessment(
                    id="risk-null-invalid", patient_id="pat-abstain", assessment_date=now,
                    model_versions={"M3": "1.0"}, input_hash="c" * 64, score=None,
                    risk_tier="unavailable", abstention=False, adjudicated_action="abstain",
                    created_at=now,
                )
            )
            session.commit()

    with pytest.raises(IntegrityError):
        with Session(engine) as session:
            session.add(
                RiskAssessment(
                    id="risk-null-wrong-action", patient_id="pat-abstain", assessment_date=now,
                    model_versions={"M3": "1.0"}, input_hash="e" * 64, score=None,
                    risk_tier="unavailable", abstention=True, adjudicated_action="needs_repeat",
                    created_at=now,
                )
            )
            session.commit()

    with Session(engine) as session:
        session.add(
            RiskAssessment(
                id="risk-null-valid", patient_id="pat-abstain", assessment_date=now,
                model_versions={"M3": "1.0"}, input_hash="d" * 64, score=None,
                risk_tier="unavailable", abstention=True, abstention_reason="insufficient_history",
                adjudicated_action="abstain", created_at=now,
            )
        )
        session.commit()

    with pytest.raises(RuntimeError, match="contain explicit abstentions"):
        command.downgrade(alembic_cfg, "b2c3d4e5f6a9")


def test_p16_governance_and_feedback_tables_are_db_enforced_append_only(temp_db_alembic):
    alembic_cfg, db_url = temp_db_alembic
    engine = create_engine(db_url)
    command.upgrade(alembic_cfg, "head")
    timestamp = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO model_governance_records
                (id, sequence, event_type, actor_id, occurred_at, payload, previous_hash, record_hash)
                VALUES ('gov-1', 1, 'shadow_evaluated', 'admin-1', :at, '{}', :prev, :hash)"""),
            {"at": timestamp, "prev": "0" * 64, "hash": "1" * 64},
        )
        connection.execute(
            text("""INSERT INTO test_ladder_feedback
                (id, facility_id, modality, available, turnaround_days, price_band, source, verified_on, submitted_by, submitted_at)
                VALUES ('fb-1', 'SITE-1', 'ct', 1, 3, 2, 'phone', :at, 'admin-1', :at)"""),
            {"at": timestamp},
        )

    for table in ("model_governance_records", "test_ladder_feedback"):
        with pytest.raises(DBAPIError, match="append-only table"):
            with engine.begin() as connection:
                connection.execute(text(f"UPDATE {table} SET id = id"))
        with pytest.raises(DBAPIError, match="append-only table"):
            with engine.begin() as connection:
                connection.execute(text(f"DELETE FROM {table}"))
    engine.dispose()


def test_quarantine_migration_preserves_legacy_m1_values(temp_db_alembic):
    alembic_cfg, db_url = temp_db_alembic
    engine = create_engine(db_url)
    command.upgrade(alembic_cfg, "heads")
    prior = {"bone": 0.4, "liver": 0.3, "lung": 0.2, "brain": 0.1}
    with Session(engine) as session:
        patient = Patient(age=50, status="active", synthetic=True)
        session.add(patient)
        session.flush()
        session.add(
            BaselineProfile(
                patient_id=patient.id,
                tumor_stage=2,
                er_status=True,
                pr_status=True,
                her2_status=False,
                has_hypertension=False,
                renal_history=False,
                target_organ_susceptibility_vector=prior,
            )
        )
        session.commit()

    command.upgrade(alembic_cfg, "head")
    with Session(engine) as session:
        baseline = session.query(BaselineProfile).one()
        assert baseline.target_organ_susceptibility_vector == prior
    engine.dispose()
