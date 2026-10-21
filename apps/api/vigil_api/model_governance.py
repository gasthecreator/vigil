"""Fail-closed shadow evaluation and human-controlled model change records (M11/J8).

This module stores only aggregate shadow metrics and governance metadata. Observation series are evaluated
in memory and never returned or written to the clinical database. It deliberately does not change clinician
inference routes; promotion changes the governance pointer only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from vigil_ml.k2 import SequentialDetector

from vigil_api.governance_attestation import verify_monitor_report
from vigil_api.models.v2 import ModelGovernanceRecord

ROOT = Path(__file__).resolve().parents[3]
MODEL_REGISTRY = ROOT / "packages/vigil-ml/vigil_ml/registry/model_registry.json"
MODEL_REGISTRY_HASH = MODEL_REGISTRY.with_suffix(".json.sha256")
CANDIDATES = ROOT / "packages/vigil-ml/vigil_ml/registry/governance_candidates.json"
CANDIDATES_HASH = CANDIDATES.with_suffix(".json.sha256")
GENESIS = "0" * 64


class GovernanceError(ValueError):
    """A rejected governance transition or failed integrity check."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_registry() -> dict[str, str]:
    """Verify generated model and governance-candidate registries against committed SHA-256 sidecars."""
    hashes: dict[str, str] = {}
    for path, sidecar in ((MODEL_REGISTRY, MODEL_REGISTRY_HASH), (CANDIDATES, CANDIDATES_HASH)):
        content = path.read_bytes()
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        actual = _sha(content)
        if not hmac.compare_digest(actual, expected):
            raise GovernanceError(f"Registry hash verification failed: {path.name}")
        hashes[path.name] = actual
    return hashes


def _candidate(candidate_id: str) -> dict[str, Any]:
    verify_registry()
    registry = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    for candidate in registry["candidates"]:
        if candidate["id"] == candidate_id:
            return candidate
    raise GovernanceError("Candidate is not present in the hash-verified allowlist")


def verify_chain(db: Session) -> list[ModelGovernanceRecord]:
    records = db.execute(
        select(ModelGovernanceRecord).order_by(ModelGovernanceRecord.sequence)
    ).scalars().all()
    previous = GENESIS
    for expected_sequence, row in enumerate(records, start=1):
        payload = {
            "sequence": expected_sequence,
            "event_type": row.event_type,
            "actor_id": row.actor_id,
            "occurred_at": (row.occurred_at.replace(tzinfo=timezone.utc) if row.occurred_at.tzinfo is None else row.occurred_at).isoformat(),
            "payload": row.payload,
            "previous_hash": previous,
        }
        digest = _sha(_canonical(payload))
        if row.sequence != expected_sequence or row.previous_hash != previous or not hmac.compare_digest(
            digest, row.record_hash
        ):
            raise GovernanceError(f"Change record chain failed verification at sequence {expected_sequence}")
        previous = row.record_hash
    return records


def _append(db: Session, event_type: str, actor_id: str, payload: dict[str, Any]) -> ModelGovernanceRecord:
    records = verify_chain(db)
    sequence = len(records) + 1
    previous = records[-1].record_hash if records else GENESIS
    now = datetime.now(timezone.utc)
    body = {
        "sequence": sequence,
        "event_type": event_type,
        "actor_id": actor_id,
        "occurred_at": now.isoformat(),
        "payload": payload,
        "previous_hash": previous,
    }
    row = ModelGovernanceRecord(
        sequence=sequence,
        event_type=event_type,
        actor_id=actor_id,
        occurred_at=now,
        payload=payload,
        previous_hash=previous,
        record_hash=_sha(_canonical(body)),
    )
    db.add(row)
    db.flush()
    return row


def _state(records: list[ModelGovernanceRecord]) -> tuple[str, dict[str, dict[str, Any]]]:
    active = "K2"
    evaluations: dict[str, dict[str, Any]] = {}
    for row in records:
        p = row.payload
        if row.event_type == "shadow_evaluated":
            evaluations[p["evaluation_id"]] = {**p, "evaluator": row.actor_id, "approval": None}
        elif row.event_type == "human_approved" and p["evaluation_id"] in evaluations:
            evaluations[p["evaluation_id"]]["approval"] = {"actor": row.actor_id, "record_id": row.id}
        elif row.event_type == "promoted":
            active = p["candidate_id"]
        elif row.event_type == "rolled_back":
            active = p["candidate_id"]
    return active, evaluations


def evaluate_shadow(
    db: Session,
    actor_id: str,
    monitor_report: dict[str, Any],
    candidate_id: str,
    max_alert_rate_increase: float,
    series: list[dict[str, Any]],
) -> dict[str, Any]:
    """Start a blinded K2 candidate evaluation only from a breached silent-monitor report."""
    if not verify_monitor_report(monitor_report):
        raise GovernanceError("Monitor report attestation is missing or invalid")
    if monitor_report.get("source") != "shadow store only" or monitor_report.get("breach") is not True:
        raise GovernanceError("A shadow-store monitor breach is required to start evaluation")
    sections = monitor_report.get("sections") or {}
    breached = sorted(name for name, value in sections.items() if isinstance(value, dict) and value.get("status") == "BREACH")
    if not breached:
        raise GovernanceError("Monitor report must contain a named BREACH section")
    if not 0 <= max_alert_rate_increase <= 1:
        raise GovernanceError("Pre-declared alert-rate criterion must be between 0 and 1")
    candidate = _candidate(candidate_id)
    if not series or any(not isinstance(item.get("observations"), list) for item in series):
        raise GovernanceError("Live-format evaluation requires non-empty observation series")

    baseline_alerts = candidate_alerts = total = 0
    code_path = Path(__import__("vigil_ml.k2", fromlist=["__file__"]).__file__)
    code_sha256 = _sha(code_path.read_bytes())
    for item in series:
        observations = item["observations"]
        baseline = SequentialDetector()
        challenger = SequentialDetector(
            alpha_pt=float(candidate["alpha_pt"]),
            sigma_log=float(candidate["sigma_log"]),
            burn_in=int(candidate["burn_in"]),
        )
        previous_day = -1.0
        for obs in observations:
            day, value = float(obs["day"]), obs.get("value")
            if day <= previous_day or (value is not None and float(value) <= 0):
                raise GovernanceError("Observation series must be chronological with positive values")
            previous_day = day
            baseline.update(day, value)
            challenger.update(day, value)
        baseline_alerts += int(baseline.alert)
        candidate_alerts += int(challenger.alert)
        total += 1

    baseline_rate = baseline_alerts / total
    candidate_rate = candidate_alerts / total
    increase = candidate_rate - baseline_rate
    criterion = {
        "name": "maximum_absolute_increase_in_series_alert_rate",
        "maximum": max_alert_rate_increase,
        "observed": increase,
        "met": increase <= max_alert_rate_increase,
    }
    evaluation_id = str(uuid4())
    hashes = verify_registry()
    monitor_digest = _sha(_canonical(monitor_report))
    if any(
        row.event_type == "shadow_evaluated" and row.payload.get("monitor_report_sha256") == monitor_digest
        for row in verify_chain(db)
    ):
        raise GovernanceError("This monitor report was already used to start an evaluation")
    payload = {
        "evaluation_id": evaluation_id,
        "candidate_id": candidate_id,
        "candidate_version": candidate["version"],
        "monitor_report_sha256": monitor_digest,
        "breached_monitors": breached,
        "predeclared_criterion": criterion,
        "series_count": total,
        "baseline_alert_series": baseline_alerts,
        "candidate_alert_series": candidate_alerts,
        "baseline_alert_rate": baseline_rate,
        "candidate_alert_rate": candidate_rate,
        "series_sha256": _sha(_canonical(series)),
        "promotion_eligible": False,
        "candidate_code_sha256": code_sha256,
        "registry_sha256": hashes,
        "evaluation_data_provenance": {
            "monitor_report": monitor_report.get("data", {}).get("provenance", "unlabeled"),
            "series": "caller_supplied_not_bound_to_attested_monitor_report",
        },
    }
    _append(db, "shadow_evaluated", actor_id, payload)
    return {**payload, "clinician_routes_unchanged": True, "patient_level_outputs_stored": False}


def approve(db: Session, actor_id: str, evaluation_id: str) -> dict[str, Any]:
    records = verify_chain(db)
    _active, evaluations = _state(records)
    evaluation = evaluations.get(evaluation_id)
    if evaluation is None:
        raise GovernanceError("Unknown evaluation")
    if not evaluation.get("promotion_eligible", False):
        raise GovernanceError(
            "Evaluation series is not bound to the attested shadow report; approval is unavailable"
        )
    if actor_id == evaluation["evaluator"]:
        raise GovernanceError("Human approval must come from a different administrator")
    if not evaluation["predeclared_criterion"]["met"]:
        raise GovernanceError("Evaluation did not meet its pre-declared promotion criterion")
    if evaluation["approval"] is not None:
        raise GovernanceError("Evaluation approval has already been recorded")
    row = _append(db, "human_approved", actor_id, {"evaluation_id": evaluation_id})
    return {"evaluation_id": evaluation_id, "approval_record_id": row.id, "approved_by": actor_id}


def promote(db: Session, actor_id: str, evaluation_id: str) -> dict[str, Any]:
    records = verify_chain(db)
    active, evaluations = _state(records)
    evaluation = evaluations.get(evaluation_id)
    if evaluation is None or evaluation["approval"] is None:
        raise GovernanceError("Promotion requires a recorded human approval")
    if not evaluation.get("promotion_eligible", False):
        raise GovernanceError("Evaluation data provenance does not permit promotion")
    if not evaluation["predeclared_criterion"]["met"]:
        raise GovernanceError("Promotion criterion was not met")
    if any(r.event_type == "promoted" and r.payload.get("evaluation_id") == evaluation_id for r in records):
        raise GovernanceError("Evaluation has already been promoted; replay refused")
    verify_registry()
    row = _append(
        db, "promoted", actor_id,
        {"evaluation_id": evaluation_id, "candidate_id": evaluation["candidate_id"], "previous_model": active},
    )
    return {"active_candidate": evaluation["candidate_id"], "change_record_id": row.id}


def rollback(db: Session, actor_id: str, reason: str) -> dict[str, Any]:
    records = verify_chain(db)
    active, _ = _state(records)
    previous = next(
        (r.payload["previous_model"] for r in reversed(records) if r.event_type == "promoted" and r.payload["candidate_id"] == active),
        None,
    )
    if previous is None:
        raise GovernanceError("No promoted candidate is available to roll back")
    row = _append(db, "rolled_back", actor_id, {"candidate_id": previous, "from_candidate": active, "reason": reason})
    return {"active_candidate": previous, "change_record_id": row.id}


def status(db: Session) -> dict[str, Any]:
    records = verify_chain(db)
    active, evaluations = _state(records)
    return {
        "registry_hashes": verify_registry(),
        "chain_valid": True,
        "active_candidate": active,
        "evaluations": list(evaluations.values()),
        "records": [
            {"id": r.id, "sequence": r.sequence, "event_type": r.event_type, "actor_id": r.actor_id,
             "occurred_at": r.occurred_at.isoformat(), "previous_hash": r.previous_hash, "record_hash": r.record_hash}
            for r in records
        ],
    }
