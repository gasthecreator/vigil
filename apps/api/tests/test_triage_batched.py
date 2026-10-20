"""Triage queue: batched implementation must equal the original per-patient (N+1) implementation.

The oracle below is a verbatim copy of the pre-optimisation endpoint body (found O(patients x queries) by the
real-HTTP load test: ~62 SQL statements per request for 10 patients). It exists only to pin behaviour.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from fastapi import Response
from sqlalchemy import create_engine, desc, event
from sqlalchemy.orm import Session
from vigil_api.api.endpoints.patients import get_triage_queue
from vigil_api.database import Base
from vigil_api.models.patient import BaselineProfile, LabResult, Patient, RiskInference
from vigil_api.models.v2 import ConsentRecord, FollowUpTask, RiskAssessment
from vigil_api.schemas.inference import TriageQueueItem


def _task_triage_oracle(db):
    """Independent N+1 oracle for the task-first ordering contract."""
    patients = db.query(Patient).all()
    rows = []
    for patient in patients:
        last_lab = (
            db.query(LabResult)
            .filter(LabResult.patient_id == patient.id)
            .order_by(desc(LabResult.date_drawn))
            .first()
        )
        total_labs = db.query(LabResult).filter(LabResult.patient_id == patient.id).count()
        active_tasks = (
            db.query(FollowUpTask)
            .filter(
                FollowUpTask.patient_id == patient.id,
                FollowUpTask.status.in_(["pending", "in_progress", "escalated"]),
            )
            .all()
        )
        selected_task = min(
            active_tasks,
            key=lambda task: (-task.escalation_level, task.due_date, task.id),
            default=None,
        )
        escalation = selected_task.escalation_level if selected_task else 0
        due_key = selected_task.due_date.timestamp() if selected_task else float("inf")
        last_lab_date = last_lab.date_drawn if last_lab else None
        recency_key = last_lab_date.timestamp() if last_lab_date else 0.0
        baseline = patient.baseline_profile
        subtype = "Unknown"
        if baseline:
            if baseline.er_status and not baseline.her2_status:
                subtype = "Luminal A (ER+/PR+)"
            elif baseline.her2_status and (baseline.er_status or baseline.pr_status):
                subtype = "Luminal B (HER2+)"
            elif baseline.her2_status:
                subtype = "HER2-Enriched"
            else:
                subtype = "Triple Negative (TNBC)"
        rows.append(
            (
                (
                    0 if active_tasks else 1,
                    -escalation,
                    due_key,
                    recency_key,
                    patient.id,
                ),
                TriageQueueItem(
                    patient_id=patient.id,
                    age=patient.age,
                    status=patient.status,
                    tumor_stage=baseline.tumor_stage if baseline else None,
                    subtype=subtype,
                    latest_risk=None,
                    triage_flag=None,
                    latest_justification="Validated recurrence-risk estimate unavailable.",
                    target_organ_susceptibility_vector=None,
                    last_lab_date=last_lab_date,
                    total_labs=total_labs,
                    action_urgency=None,
                    urgency_breakdown=None,
                ),
            )
        )
    rows.sort(key=lambda row: row[0])
    return [item for _, item in rows]


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
    new = _as_rows(get_triage_queue(response=Response(), limit=1000, offset=0, db=db, current_user=None))
    old = _as_rows(_task_triage_oracle(db))
    assert len(new) == len(old) == 14
    assert [r["patient_id"] for r in new] == [r["patient_id"] for r in old]
    for a, b in zip(new, old):
        for k in a:
            if isinstance(a[k], float) and isinstance(b[k], float):
                assert a[k] == pytest.approx(b[k], abs=2e-3), k
            elif k == "urgency_breakdown":
                assert a[k] == b[k], k
            else:
                assert a[k] == b[k], k


def test_triage_statement_count_does_not_scale_with_patients(db):
    _seed(db, 24)
    counts: List[int] = []
    eng = db.get_bind()
    event.listen(eng, "before_cursor_execute", lambda *a, **k: counts.append(1))
    get_triage_queue(response=Response(), limit=1000, offset=0, db=db, current_user=None)
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
        new = _as_rows(get_triage_queue(response=Response(), limit=1000, offset=0, db=db, current_user=None))
    finally:
        event.remove(FollowUpTask, "load", _count)
    assert not loaded, f"{len(loaded)} FollowUpTask rows materialised"
    old = {r["patient_id"]: r for r in _as_rows(_task_triage_oracle(db))}
    for r in new:
        assert r["action_urgency"] is old[r["patient_id"]]["action_urgency"] is None
        assert r["latest_risk"] is old[r["patient_id"]]["latest_risk"] is None


def test_triage_uses_due_date_and_escalation_from_the_same_task(db):
    _seed(db, 3)
    db.query(FollowUpTask).filter(FollowUpTask.patient_id.in_(["P01", "P02"])).delete(
        synchronize_session=False
    )
    db.add_all(
        [
            FollowUpTask(
                patient_id="P01",
                task_type="repeat_lab",
                status="pending",
                due_date=NOW + timedelta(days=10),
                escalation_level=3,
            ),
            FollowUpTask(
                patient_id="P01",
                task_type="repeat_lab",
                status="pending",
                due_date=NOW - timedelta(days=30),
                escalation_level=0,
            ),
            FollowUpTask(
                patient_id="P02",
                task_type="repeat_lab",
                status="pending",
                due_date=NOW + timedelta(days=5),
                escalation_level=3,
            ),
        ]
    )
    db.commit()

    queue = get_triage_queue(response=Response(), limit=100, offset=0, db=db, current_user=None)
    ids = [item.patient_id for item in queue]
    assert ids.index("P02") < ids.index("P01") < ids.index("P00")
    assert [item.patient_id for item in queue] == [
        item.patient_id for item in _task_triage_oracle(db)
    ]


def test_triage_pagination_preserves_order_and_reports_total(db):
    """Paging must return exactly the same ordered rows as the full queue and report the total (scale fix)."""
    _seed(db)
    full_resp = Response()
    full = get_triage_queue(response=full_resp, limit=1000, offset=0, db=db, current_user=None)
    assert full_resp.headers["x-total-count"] == str(len(full)) == "14"
    page1_resp, page2_resp = Response(), Response()
    p1 = get_triage_queue(response=page1_resp, limit=5, offset=0, db=db, current_user=None)
    p2 = get_triage_queue(response=page2_resp, limit=5, offset=5, db=db, current_user=None)
    assert [x.patient_id for x in p1 + p2] == [x.patient_id for x in full[:10]]
    assert page1_resp.headers["x-total-count"] == "14"
    assert all(x.action_urgency is None for x in full)
