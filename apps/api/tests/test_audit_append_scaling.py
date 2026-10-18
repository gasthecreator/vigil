"""Audit append cost must not grow with the size of the audit log.

Found by the real-HTTP load test: ``record_audit_event`` loaded every AuditEvent row twice per
append (leaf lookup and event count), so p95 latency grew with history and concurrent writers queued.
These tests pin the behaviour: the leaf found by the fast path equals the legacy definition (the event whose
``curr_hash`` is nobody's ``prev_hash``), the chain verifies, the fast path survives a damaged anchor by
falling back, and the number of AuditEvent rows materialised per append is bounded independent of N.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from vigil_api.audit import get_latest_audit_event, record_audit_event, verify_audit_chain
from vigil_api.database import Base
from vigil_api.models.v2 import AuditAnchor, AuditEvent


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'scale.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    return eng


def _append(session: Session, i: int, t0: datetime) -> AuditEvent:
    ev = record_audit_event(session, "u1", "admin", "test.append", "patient", f"P{i}", {"i": i}, timestamp=t0 + timedelta(seconds=i))
    session.commit()
    return ev


def _legacy_leaf(session: Session) -> str | None:
    events = session.execute(select(AuditEvent)).scalars().all()
    prevs = {e.prev_hash for e in events}
    leaves = [e.curr_hash for e in events if e.curr_hash not in prevs]
    return leaves[0] if leaves else None


def test_fast_leaf_equals_legacy_definition_and_chain_verifies(engine):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with Session(engine) as s:
        for i in range(60):
            ev = _append(s, i, t0)
            assert get_latest_audit_event(s).curr_hash == ev.curr_hash == _legacy_leaf(s)
        assert verify_audit_chain(s)["valid"] is True
        assert s.execute(select(AuditAnchor)).scalars().first().total_events == 60


def test_append_materialises_a_bounded_number_of_rows_regardless_of_log_size(engine):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    loaded: list[int] = []
    with Session(engine) as s:
        for i in range(150):
            _append(s, i, t0)
        def _count(*_a, **_k):
            loaded.append(1)

        event.listen(AuditEvent, "load", _count)
        try:
            _append(s, 150, t0)
        finally:
            event.remove(AuditEvent, "load", _count)
        # one leaf (+ at most one identity refresh); never O(N). N = 150 here, so a full scan would be >= 150.
        assert len(loaded) <= 4, f"{len(loaded)} AuditEvent rows loaded for one append"


def test_damaged_anchor_falls_back_to_chain_scan(engine):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with Session(engine) as s:
        for i in range(10):
            last = _append(s, i, t0)
        anchor = s.execute(select(AuditAnchor)).scalars().first()
        anchor.head_hash = "f" * 64  # points at no event
        s.commit()
        assert get_latest_audit_event(s).curr_hash == last.curr_hash
        nxt = _append(s, 10, t0)
        assert nxt.prev_hash == last.curr_hash
        assert verify_audit_chain(s)["valid"] is True


def test_stale_anchor_pointing_at_a_non_leaf_falls_back(engine):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with Session(engine) as s:
        first = _append(s, 0, t0)
        for i in range(1, 8):
            last = _append(s, i, t0)
        anchor = s.execute(select(AuditAnchor)).scalars().first()
        anchor.head_hash = first.curr_hash  # a real event, but not the leaf
        s.commit()
        assert get_latest_audit_event(s).curr_hash == last.curr_hash
