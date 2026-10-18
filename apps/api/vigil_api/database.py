"""SQLAlchemy database connection and session management."""

import threading
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from vigil_api.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite is the local/dev/staging-single-node database (PostgreSQL is the multi-writer target).
    # Defaults (rollback journal, 5 s busy wait, deferred transactions) made concurrent writers fail with
    # "database is locked" (HTTP 500) in the real-HTTP load test. WAL lets readers proceed during a write and
    # busy_timeout makes writers queue instead of failing.
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - exercised by the load test
        cur = dbapi_connection.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA busy_timeout=30000")
        finally:
            cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite has one writer at a time and its busy handler polls with back-off, which is unfair: a few unlucky
    # writers waited seconds (p99 > 2 s) while others finished at once. Writers of this process therefore queue on
    # one lock taken before a session's first write and released when its outermost transaction ends, so waits are
    # bounded by the work of the writers ahead. Readers are not serialised (WAL). Not used for PostgreSQL.
    _SQLITE_WRITE_LOCK = threading.Lock()
    _SQLITE_WRITE_LOCK_TIMEOUT_S = 30.0
    _HELD = "_vigil_sqlite_write_lock_held"

    @event.listens_for(SessionLocal, "before_flush")
    def _acquire_write_lock(session, _ctx, _instances):
        if session.info.get(_HELD):
            return
        if not (session.new or session.dirty or session.deleted):
            return
        if not _SQLITE_WRITE_LOCK.acquire(timeout=_SQLITE_WRITE_LOCK_TIMEOUT_S):
            from sqlalchemy.exc import OperationalError

            raise OperationalError("acquire sqlite write lock", {}, TimeoutError("sqlite write lock wait exceeded 30 s"))
        session.info[_HELD] = True

    @event.listens_for(SessionLocal, "after_transaction_end")
    def _release_write_lock(session, transaction):
        if transaction.parent is None and session.info.pop(_HELD, False):
            _SQLITE_WRITE_LOCK.release()

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
