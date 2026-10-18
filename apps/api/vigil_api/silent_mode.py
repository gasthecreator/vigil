"""Silent mode: the write facade used by the ingestion pipeline (PREREGISTRATION.md section 6).

In silent mode every model output (risk assessment, alert, follow-up task, adjudicated action, K2 state)
goes to the shadow store instead of the clinical database, and the HTTP response says the outputs are
withheld. The decision is taken from server settings only; a request body, header or query parameter cannot
change it. If the shadow store is unavailable the request fails (HTTP 503) and nothing is committed to the
clinical database: silent mode never falls back to showing or storing outputs in the clinical database.

This module deliberately exposes no function that returns predictions or outcomes. Reading the shadow store
is the job of ``vigil_api.silent_monitoring`` and of operator scripts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from vigil_api.config import settings
from vigil_api.shadow_store import (
    ShadowDetectorState,
    ShadowIngestRejection,
    ShadowPrediction,
    ShadowStore,
    get_store,
)

WITHHELD_ACTION = "withheld_silent_mode"
BLOCKED_CODE = "silent_mode_blocked"

# Public names that the import-rule test allows other modules to use.
PUBLIC_API = (
    "WITHHELD_ACTION",
    "BLOCKED_CODE",
    "is_silent",
    "block_in_silent_mode",
    "record_prediction",
    "record_rejection",
    "load_detector_state",
    "save_detector_state",
)


def is_silent() -> bool:
    """True when the server runs in silent mode (server settings only)."""
    return bool(settings.SILENT_MODE)


def _store() -> ShadowStore:
    url = settings.SILENT_SHADOW_DATABASE_URL
    if not url or url == settings.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Silent mode is on but no separate shadow store is configured; request refused.",
        )
    try:
        return get_store(url)
    except Exception as exc:  # fail closed
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Silent mode shadow store unavailable ({type(exc).__name__}); request refused.",
        ) from exc


def block_in_silent_mode(feature: str) -> None:
    """Refuse a route whose response is itself a model output (HTTP 409 in silent mode)."""
    if is_silent():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": BLOCKED_CODE,
                "message": f"{feature} returns model output and is disabled while the system "
                "runs in silent mode.",
            },
        )


def record_prediction(
    *,
    patient_id: str,
    observation_id: str,
    analyte_code: str,
    specimen_collected_at: datetime,
    canonical_value: float,
    score: float,
    score_kind: str,
    m3_action: str,
    risk_tier: str,
    would_alert: bool,
    alert_type: Optional[str],
    severity: Optional[str],
    p_error: Optional[float] = None,
    p_stable: Optional[float] = None,
    k2_log_e: Optional[float] = None,
    k2_tier: Optional[str] = None,
    k2_alert: Optional[bool] = None,
    plausibility_status: Optional[str] = None,
    model_versions: Optional[Dict[str, Any]] = None,
    input_hash: Optional[str] = None,
) -> None:
    """Write one prediction to the shadow store (committed immediately)."""
    store = _store()
    with store.session() as session:
        session.add(
            ShadowPrediction(
                patient_id=patient_id,
                observation_id=observation_id,
                analyte_code=analyte_code,
                specimen_collected_at=specimen_collected_at,
                canonical_value=canonical_value,
                score=score,
                score_kind=score_kind,
                p_error=p_error,
                p_stable=p_stable,
                m3_action=m3_action,
                k2_log_e=k2_log_e,
                k2_tier=k2_tier,
                k2_alert=k2_alert,
                risk_tier=risk_tier,
                would_alert=would_alert,
                alert_type=alert_type,
                severity=severity,
                plausibility_status=plausibility_status,
                model_versions=model_versions,
                input_hash=input_hash,
            )
        )
        session.commit()


def load_detector_state(patient_id: str) -> Optional[Dict[str, Any]]:
    """K2 state for the next update of the same pipeline; never surfaced to a client."""
    store = _store()
    with store.session() as session:
        row = session.get(ShadowDetectorState, patient_id)
        return dict(row.state) if row is not None else None


def save_detector_state(patient_id: str, state: Dict[str, Any]) -> None:
    store = _store()
    with store.session() as session:
        row = session.get(ShadowDetectorState, patient_id)
        if row is None:
            session.add(ShadowDetectorState(patient_id=patient_id, state=state))
        else:
            row.state = state
        session.commit()


def record_rejection(analyte_code: str, reason: str) -> None:
    """Count a refused ingestion for the data-shift monitor (no values are stored)."""
    store = _store()
    with store.session() as session:
        session.add(ShadowIngestRejection(analyte_code=str(analyte_code)[:50], reason=reason))
        session.commit()
