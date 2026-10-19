"""SQLite writers of one process queue on a lock (taken at first write, released when the transaction ends).

Without it SQLite's polling busy handler is unfair: in the real-HTTP load test a few lab POSTs waited >2 s
(p99) while their neighbours finished at once. These tests pin the mechanism deterministically (no timing).
"""

from __future__ import annotations

import threading

import pytest
from sqlalchemy import create_engine
from vigil_api import database
from vigil_api.models.v2 import Facility

pytestmark = [
    pytest.mark.sqlite_only,
    pytest.mark.skipif(
        not database.settings.DATABASE_URL.startswith("sqlite"),
        reason="SQLite-only mechanism",
    ),
]


@pytest.fixture
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'w.db'}", connect_args={"check_same_thread": False})
    database.Base.metadata.create_all(bind=eng)
    return eng


def _write(session, fid: str) -> None:
    session.add(Facility(id=fid, name=fid, code=fid))
    session.flush()


def test_second_writer_waits_until_first_commits(engine):
    a, b = database.SessionLocal(bind=engine), database.SessionLocal(bind=engine)
    _write(a, "F-A")
    assert database._SQLITE_WRITE_LOCK.locked(), "the in-process write lock must be held after a session's first write"
    entered = threading.Event()
    done = threading.Event()

    def other():
        entered.set()
        _write(b, "F-B")  # must block here until A's transaction ends
        done.set()
        b.commit()

    t = threading.Thread(target=other)
    t.start()
    assert entered.wait(5)
    assert not done.wait(0.3), "writer B ran while writer A still held the write transaction"
    a.commit()
    assert done.wait(10), "writer B never proceeded after A committed"
    t.join(10)
    a.close()
    b.close()


@pytest.mark.parametrize("end", ["rollback", "close"])
def test_lock_is_released_on_rollback_and_close(engine, end):
    a = database.SessionLocal(bind=engine)
    _write(a, "F-A")
    getattr(a, end)()
    b = database.SessionLocal(bind=engine)
    result: list[str] = []
    t = threading.Thread(target=lambda: (_write(b, "F-B"), b.commit(), result.append("ok")))
    t.start()
    t.join(10)
    assert result == ["ok"], f"lock leaked after {end}"
    b.close()


def test_read_only_session_never_takes_the_lock(engine):
    a = database.SessionLocal(bind=engine)
    a.query(Facility).all()
    assert not a.info.get(database._HELD)
    _write(a, "F-A")
    assert a.info.get(database._HELD)
    a.rollback()
    assert not a.info.get(database._HELD)
    a.close()
