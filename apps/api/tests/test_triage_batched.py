"""Triage queue: batched implementation must equal the original per-patient (N+1) implementation.

The oracle below is a verbatim copy of the pre-optimisation endpoint body (found O(patients x queries) by the
real-HTTP load test: ~62 SQL statements per request for 10 patients). It exists only to pin behaviour.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from sqlalchemy import create_engine, desc, event
from sqlalchemy.orm import Session
from vigil_api.api.endpoints.patients import get_triage_queue
from vigil_api.database import Base
from vigil_api.models.patient import BaselineProfile, LabResult, Patient, RiskInference
from vigil_api.models.v2 import ConsentRecord, FollowUpTask, RiskAssessment
from vigil_api.schemas.inference import TriageQueueItem


def _legacy_triage(db):
    # Verbatim copy of the pre-optimisation get_triage_queue body (N+1 queries). Oracle only.

    now = datetime.now(timezone.utc)
    patients = db.query(Patient).all()
    triage_roster: List[TriageQueueItem] = []

    for patient in patients:
        # Find latest risk inference
        latest_inference = (
            db.query(RiskInference)
            .filter(RiskInference.patient_id == patient.id)
            .order_by(desc(RiskInference.created_at))
            .first()
        )

        baseline = patient.baseline_profile
        subtype = "Unknown"
        organ_vector = None
        tumor_stage = None

        if baseline:
            tumor_stage = baseline.tumor_stage
            organ_vector = baseline.target_organ_susceptibility_vector
            if baseline.er_status and not baseline.her2_status:
                subtype = "Luminal A (ER+/PR+)"
            elif baseline.her2_status and (baseline.er_status or baseline.pr_status):
                subtype = "Luminal B (HER2+)"
            elif baseline.her2_status:
                subtype = "HER2-Enriched"
            else:
                subtype = "Triple Negative (TNBC)"

        last_lab = (
            db.query(LabResult)
            .filter(LabResult.patient_id == patient.id)
            .order_by(desc(LabResult.date_drawn))
            .first()
        )
        total_labs = db.query(LabResult).filter(LabResult.patient_id == patient.id).count()

        latest_risk = latest_inference.calculated_metastasis_risk if latest_inference else 0.0
        triage_flag = latest_inference.triage_flag if latest_inference else False
        justification = (
            latest_inference.justification_text
            if latest_inference
            else "Awaiting initial surveillance lab draw."
        )

        # 1. Risk component (weight 0.40)
        s_risk = float(latest_risk)

        # 2. Uncertainty / Abstention component (weight 0.25)
        latest_assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.patient_id == patient.id)
            .order_by(desc(RiskAssessment.created_at))
            .first()
        )
        if latest_assessment:
            if latest_assessment.abstention:
                s_unc = 1.0
            else:
                p_err = (latest_assessment.uncertainty or {}).get("p_error", 0.0)
                margin = 0.04 * (1.0 - abs(latest_assessment.score - 0.5))
                s_unc = min(1.0, max(float(p_err), float(2.0 * margin)))
        else:
            margin = 0.04 * (1.0 - abs(latest_risk - 0.5))
            s_unc = min(1.0, float(2.0 * margin))

        # 3. Overdue follow-up tasks component (weight 0.20)
        active_tasks = (
            db.query(FollowUpTask)
            .filter(
                FollowUpTask.patient_id == patient.id,
                FollowUpTask.status.in_(["pending", "in_progress", "escalated"]),
            )
            .all()
        )
        max_overdue_days = 0.0
        max_escalation = 0
        for task in active_tasks:
            due = (
                task.due_date
                if task.due_date.tzinfo
                else task.due_date.replace(tzinfo=timezone.utc)
            )
            overdue_days = max(0.0, (now - due).total_seconds() / 86400.0)
            if overdue_days > max_overdue_days:
                max_overdue_days = overdue_days
            if task.escalation_level > max_escalation:
                max_escalation = task.escalation_level

        if active_tasks:
            s_overdue = min(1.0, max(max_overdue_days / 14.0, max_escalation / 3.0))
        else:
            s_overdue = 0.0

        # 4. Treatment / surveillance delay component (weight 0.15)
        if last_lab and last_lab.date_drawn:
            lab_date = (
                last_lab.date_drawn
                if last_lab.date_drawn.tzinfo
                else last_lab.date_drawn.replace(tzinfo=timezone.utc)
            )
            days_since = max(0.0, (now - lab_date).total_seconds() / 86400.0)
            if days_since > 90.0:
                s_delay = min(1.0, (days_since - 90.0) / 90.0)
            else:
                s_delay = 0.0
        else:
            s_delay = 0.5

        # Composite Action Urgency
        action_urgency = round(
            0.40 * s_risk + 0.25 * s_unc + 0.20 * s_overdue + 0.15 * s_delay,
            4,
        )
        urgency_breakdown = {
            "risk_component": round(0.40 * s_risk, 4),
            "uncertainty_component": round(0.25 * s_unc, 4),
            "overdue_component": round(0.20 * s_overdue, 4),
            "delay_component": round(0.15 * s_delay, 4),
        }

        triage_roster.append(
            TriageQueueItem(
                patient_id=patient.id,
                age=patient.age,
                status=patient.status,
                tumor_stage=tumor_stage,
                subtype=subtype,
                latest_risk=latest_risk,
                triage_flag=triage_flag,
                latest_justification=justification,
                target_organ_susceptibility_vector=organ_vector,
                last_lab_date=last_lab.date_drawn if last_lab else None,
                total_labs=total_labs,
                action_urgency=action_urgency,
                urgency_breakdown=urgency_breakdown,
            )
        )

    # Sort strictly descending by action_urgency, breaking ties by latest_risk and recency
    triage_roster.sort(
        key=lambda x: (
            x.action_urgency,
            x.latest_risk,
            x.last_lab_date.timestamp() if x.last_lab_date else 0.0,
        ),
        reverse=True,
    )
    return triage_roster


NOW = datetime.now(timezone.utc)


@pytest.fixture
def db(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 't.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    with Session(eng) as s:
        yield s


def _seed(s: Session, n: int = 14) -> None:
    for i in range(n):
        p = Patient(id=f"P{i:02d}", mrn=f"M{i}", age=40 + i, synthetic=True, status="active" if i % 5 else "monitoring")
        s.add(p)
        s.flush()
        # the triage queue only lists patients with active consent
        s.add(ConsentRecord(patient_id=p.id, consent_type="surveillance_monitoring", granted=True, scope="full", granted_at=NOW))
        if i % 3 != 2:  # some patients have no baseline
            s.add(BaselineProfile(patient_id=p.id, tumor_stage=1 + i % 4, er_status=i % 2 == 0, pr_status=i % 4 == 0,
                                  her2_status=i % 3 == 0, target_organ_susceptibility_vector={"bone": 0.1 * (i % 5)}))
        if i % 4 != 3:  # some have no labs at all
            for j in range(1 + i % 5):
                lab = LabResult(patient_id=p.id, date_drawn=(NOW - timedelta(days=(i * 13 + j * 31) % 170)).replace(tzinfo=None),
                                alt_level=20.0, ast_level=20.0, creatinine=0.9, ca_15_3=15.0, wbc_count=6.0)
                s.add(lab)
                s.flush()
                s.add(RiskInference(patient_id=p.id, lab_result_id=lab.id, calculated_metastasis_risk=((i * 7 + j * 11) % 100) / 100.0,
                                    triage_flag=(i + j) % 3 == 0, justification_text=f"j{i}-{j}",
                                    created_at=(NOW - timedelta(days=60 - j * 5 - i)).replace(tzinfo=None)))
        if i % 2 == 0:
            s.add(RiskAssessment(patient_id=p.id, model_versions={"M3": "1"}, input_hash="h" * 64, score=0.2 + 0.05 * i,
                                 abstention=(i % 6 == 0), uncertainty={"p_error": 0.1 * (i % 4)}, created_at=NOW - timedelta(days=i)))
            s.add(RiskAssessment(patient_id=p.id, model_versions={"M3": "1"}, input_hash="g" * 64, score=0.9 - 0.03 * i,
                                 abstention=False, uncertainty={"p_error": 0.05}, created_at=NOW - timedelta(days=i + 3)))
        for k in range(i % 3):
            s.add(FollowUpTask(patient_id=p.id, task_type="repeat_lab", status=["pending", "completed", "escalated"][k % 3],
                               due_date=NOW - timedelta(days=3 * i + k), escalation_level=k))
    s.commit()


def _as_rows(items: List[TriageQueueItem]):
    return [i.model_dump(mode="json") for i in items]


def test_batched_triage_equals_legacy_implementation(db):
    _seed(db)
    new = _as_rows(get_triage_queue(db=db, current_user=None))
    old = _as_rows(_legacy_triage(db))
    assert len(new) == len(old) == 14
    assert [r["patient_id"] for r in new] == [r["patient_id"] for r in old]
    for a, b in zip(new, old):
        for k in a:
            if isinstance(a[k], float):
                assert a[k] == pytest.approx(b[k], abs=2e-3), k
            elif k == "urgency_breakdown":
                for kk in a[k]:
                    assert a[k][kk] == pytest.approx(b[k][kk], abs=2e-3), kk
            else:
                assert a[k] == b[k], k


def test_triage_statement_count_does_not_scale_with_patients(db):
    _seed(db, 24)
    counts: List[int] = []
    eng = db.get_bind()
    event.listen(eng, "before_cursor_execute", lambda *a, **k: counts.append(1))
    get_triage_queue(db=db, current_user=None)
    assert len(counts) <= 10, f"{len(counts)} SQL statements for 24 patients"


def test_triage_does_not_materialise_every_pending_task(db):
    _seed(db, 6)
    for k in range(400):
        db.add(FollowUpTask(patient_id="P01", task_type="repeat_lab", status="pending", due_date=NOW - timedelta(days=k % 30), escalation_level=k % 3))
    db.commit()
    loaded: List[int] = []

    def _count(*_a, **_k):
        loaded.append(1)

    event.listen(FollowUpTask, "load", _count)
    try:
        new = _as_rows(get_triage_queue(db=db, current_user=None))
    finally:
        event.remove(FollowUpTask, "load", _count)
    assert not loaded, f"{len(loaded)} FollowUpTask rows materialised"
    old = {r["patient_id"]: r for r in _as_rows(_legacy_triage(db))}
    for r in new:
        assert r["action_urgency"] == pytest.approx(old[r["patient_id"]]["action_urgency"], abs=2e-3)
