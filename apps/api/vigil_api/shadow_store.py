"""Shadow store for silent mode (PREREGISTRATION.md section 6, tier T-Q).

The shadow store is a **separate database** with its own engine, its own declarative base and its own
session factory. Nothing here shares metadata, connection or session with ``vigil_api.database``, so the
clinician-facing ORM session cannot see these tables, and a SQL statement issued through it (including an
injected one) cannot reach them.

Import rule, enforced by ``apps/api/tests/test_silent_mode.py``: only ``vigil_api.silent_mode`` (the write
facade used by the ingestion pipeline), ``vigil_api.silent_monitoring`` and operator scripts may import this
module. No module under ``vigil_api/api/`` may import it, and there is no HTTP route that reads it.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    String,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

ShadowBase = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ShadowPrediction(ShadowBase):
    """One model output that the clinician-facing system never sees."""

    __tablename__ = "shadow_predictions"

    id = Column(String(36), primary_key=True, default=_uuid)
    recorded_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)
    patient_id = Column(String(36), nullable=False, index=True)
    observation_id = Column(String(36), nullable=False, index=True)
    analyte_code = Column(String(50), nullable=False)
    specimen_collected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    canonical_value = Column(Float, nullable=False)
    # The quantity the monitor treats as the model's risk score. For the M3/K2 pipeline this is M3's
    # probability that the change is real (not a recurrence-risk probability); score_kind says so.
    score = Column(Float, nullable=False)
    score_kind = Column(String(50), nullable=False)
    p_error = Column(Float, nullable=True)
    p_stable = Column(Float, nullable=True)
    m3_action = Column(String(50), nullable=False)
    k2_log_e = Column(Float, nullable=True)
    k2_tier = Column(String(50), nullable=True)
    k2_alert = Column(Boolean, nullable=True)
    risk_tier = Column(String(20), nullable=False)
    would_alert = Column(Boolean, nullable=False, index=True)
    alert_type = Column(String(50), nullable=True)
    severity = Column(String(20), nullable=True)
    plausibility_status = Column(String(50), nullable=True)
    model_versions = Column(JSON, nullable=True)
    input_hash = Column(String(64), nullable=True)
    # Conformal set (list of labels) and its nominal level, when the producing model supplies one. The M3/K2
    # pipeline does not, so these stay NULL and the monitor reports coverage as not measurable.
    conformal_set = Column(JSON, nullable=True)
    conformal_nominal = Column(Float, nullable=True)


Index("ix_shadow_pred_patient_time", ShadowPrediction.patient_id, ShadowPrediction.specimen_collected_at)


class ShadowDetectorState(ShadowBase):
    """K2 sequential-detector state in silent mode (kept out of the clinician-visible patient row)."""

    __tablename__ = "shadow_detector_states"

    patient_id = Column(String(36), primary_key=True)
    state = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class ShadowOutcome(ShadowBase):
    """Clinical outcomes imported by the data steward (never entered through a clinician route)."""

    __tablename__ = "shadow_outcomes"

    id = Column(String(36), primary_key=True, default=_uuid)
    patient_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(30), nullable=False)  # recurrence_confirmed | last_followup | death_other
    event_time = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(100), nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class ShadowIngestRejection(ShadowBase):
    """A refused ingestion (unit or registry error), counted for the data-shift monitor. No values are kept."""

    __tablename__ = "shadow_ingest_rejections"

    id = Column(String(36), primary_key=True, default=_uuid)
    recorded_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)
    analyte_code = Column(String(50), nullable=False, index=True)
    reason = Column(String(30), nullable=False)  # unit | unregistered_analyte


OUTCOME_TYPES = ("recurrence_confirmed", "last_followup", "death_other")
REJECTION_REASONS = ("unit", "unregistered_analyte")


class ShadowStore:
    """A connection to one shadow database."""

    def __init__(self, url: str) -> None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.url = url
        self.engine: Engine = create_engine(url, connect_args=connect_args, echo=False)
        if url.startswith("sqlite"):

            @event.listens_for(self.engine, "connect")
            def _pragmas(dbapi_connection, _record):  # pragma: no cover - sqlite specific
                cur = dbapi_connection.cursor()
                try:
                    cur.execute("PRAGMA journal_mode=WAL")
                    cur.execute("PRAGMA busy_timeout=30000")
                finally:
                    cur.close()

        ShadowBase.metadata.create_all(bind=self.engine)
        self._factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def session(self) -> Session:
        return self._factory()

    def dispose(self) -> None:
        self.engine.dispose()


_STORES: Dict[str, ShadowStore] = {}
_LOCK = threading.Lock()


def get_store(url: str) -> ShadowStore:
    """Return the (cached) store for ``url``."""
    with _LOCK:
        store = _STORES.get(url)
        if store is None:
            store = ShadowStore(url)
            _STORES[url] = store
        return store


def reset_stores() -> None:
    """Dispose cached stores (tests, process shutdown)."""
    with _LOCK:
        for store in _STORES.values():
            store.dispose()
        _STORES.clear()
