"""Hash-Chained Append-Only Audit Trail Engine.

Implements Master Plan §11 and Phase 5a Audit requirements:
- Cryptographic SHA-256 hash chaining of all clinical actions.
- Verification engine detecting broken links or altered event contents.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from vigil_api.models.v2 import (
    AuditAnchor,
    AuditEvent,
    audit_hash_candidates,
    calculate_audit_hash,
)


def _scan_for_leaf(db: Session) -> Optional[AuditEvent]:
    """Reference definition of the leaf: the event whose ``curr_hash`` is nobody's ``prev_hash``. O(N)."""
    all_events = db.execute(select(AuditEvent)).scalars().all()
    if not all_events:
        return None
    prev_set = {e.prev_hash for e in all_events}
    for e in all_events:
        if e.curr_hash not in prev_set:
            return e
    return all_events[-1]


def get_latest_audit_event(db: Session) -> Optional[AuditEvent]:
    """Find the current leaf node of the cryptographic audit chain.

    Fast path (O(log N)): the chain head recorded in the AuditAnchor row, accepted only if that event exists
    and no event names it as ``prev_hash`` (i.e. it really is a leaf). Anything else (no anchor, anchor pointing
    at no event or at a non-leaf, an empty table) falls back to the full scan, so the result is the same as the
    reference definition whenever the fast path applies and the legacy behaviour otherwise.
    """
    anchor = db.execute(select(AuditAnchor).order_by(AuditAnchor.created_at.desc())).scalars().first()
    if anchor is not None:
        candidate = db.execute(select(AuditEvent).where(AuditEvent.curr_hash == anchor.head_hash).limit(1)).scalars().first()
        if candidate is not None:
            has_child = db.execute(select(exists().where(AuditEvent.prev_hash == candidate.curr_hash))).scalar()
            if not has_child:
                return candidate
    return _scan_for_leaf(db)


def record_audit_event(
    db: Session,
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> AuditEvent:
    """Append a cryptographically chained audit event to the ledger."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Get the latest audit event leaf to link against
    latest_event = get_latest_audit_event(db)
    prev_hash = latest_event.curr_hash if latest_event else "0" * 64

    curr_hash = calculate_audit_hash(
        prev_hash=prev_hash,
        timestamp=timestamp,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )

    event = AuditEvent(
        timestamp=timestamp,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        prev_hash=prev_hash,
        curr_hash=curr_hash,
    )
    db.add(event)
    db.flush()

    # Update or persist external head-hash anchor (Condition S5-3 / P7-D)
    total_events = db.execute(select(func.count()).select_from(AuditEvent)).scalar_one()
    anchor_path = os.environ.get("VIGIL_AUDIT_ANCHOR_PATH")
    if anchor_path:
        p = Path(anchor_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": timestamp.isoformat(),
            "total_events": total_events,
            "head_hash": curr_hash,
        }
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    anchor = (
        db.execute(select(AuditAnchor).order_by(AuditAnchor.created_at.desc())).scalars().first()
    )
    if anchor is None:
        anchor = AuditAnchor(
            head_hash=curr_hash,
            total_events=total_events,
            created_at=timestamp,
        )
        db.add(anchor)
    else:
        anchor.head_hash = curr_hash
        anchor.total_events = total_events
        anchor.created_at = timestamp
    db.flush()

    return event


def verify_audit_chain(
    db: Session,
    expected_head_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify cryptographic integrity of the entire audit event chain.

    Checks:
    1. Cryptographic SHA-256 payload and linkage from genesis (0*64) to head.
    2. Consistency against the external AuditAnchor (VIGIL_AUDIT_ANCHOR_PATH) to detect tail deletion attacks,
       even if the database and its internal tables are completely rewritten.
    """
    anchor_path = os.environ.get("VIGIL_AUDIT_ANCHOR_PATH")
    ext_anchor = None
    if anchor_path and os.path.exists(anchor_path) and os.path.getsize(anchor_path) > 0:
        with open(anchor_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        if lines:
            try:
                ext_anchor = json.loads(lines[-1])
            except Exception:
                parts = lines[-1].split(",")
                if len(parts) >= 3:
                    ext_anchor = {
                        "timestamp": parts[0],
                        "total_events": int(parts[1]),
                        "head_hash": parts[2],
                    }

    events = db.execute(select(AuditEvent)).scalars().all()
    if not events:
        if ext_anchor is not None and int(ext_anchor.get("total_events", 0)) > 0:
            return {
                "valid": False,
                "error": f"Tail deletion detected: audit ledger is empty but external anchor records {ext_anchor.get('total_events')} events.",
                "verified_events": 0,
                "total_events": 0,
                "head_hash": "0" * 64,
                "anchored_head_hash": ext_anchor.get("head_hash"),
            }
        anchor = (
            db.execute(select(AuditAnchor).order_by(AuditAnchor.created_at.desc()))
            .scalars()
            .first()
        )
        if anchor is not None and anchor.total_events > 0:
            return {
                "valid": False,
                "error": f"Tail deletion detected: audit ledger is empty but anchor records {anchor.total_events} events.",
                "verified_events": 0,
                "total_events": 0,
                "head_hash": "0" * 64,
                "anchored_head_hash": anchor.head_hash,
            }
        return {
            "valid": True,
            "verified_events": 0,
            "total_events": 0,
            "head_hash": "0" * 64,
        }

    by_prev = {ev.prev_hash: ev for ev in events}
    expected_prev = "0" * 64
    verified_count = 0
    scheme_counts: Dict[str, int] = {}

    while expected_prev in by_prev:
        ev = by_prev[expected_prev]
        candidates = audit_hash_candidates(
            prev_hash=ev.prev_hash,
            timestamp=ev.timestamp,
            actor_id=ev.actor_id,
            actor_role=ev.actor_role,
            action=ev.action,
            resource_type=ev.resource_type,
            resource_id=ev.resource_id,
            details=ev.details,
        )
        matched = [scheme for scheme, digest in candidates.items() if digest == ev.curr_hash]

        if not matched:
            return {
                "valid": False,
                "error": f"Tampered payload at index {verified_count}: curr_hash '{ev.curr_hash}' does not match recomputed hash '{candidates['v1-canonical-utc']}'",
                "tampered_event_id": ev.id,
                "verified_events": verified_count,
                "total_events": len(events),
            }

        scheme_counts[matched[0]] = scheme_counts.get(matched[0], 0) + 1
        expected_prev = ev.curr_hash
        verified_count += 1

    if verified_count != len(events):
        orphans = [
            e for e in events if e.curr_hash != expected_prev and e.prev_hash != expected_prev
        ]
        orphan_id = orphans[0].id if orphans else "unknown"
        return {
            "valid": False,
            "error": f"Chain link broken at index {verified_count}: expected next link from '{expected_prev}', but link is missing or disconnected.",
            "tampered_event_id": orphan_id,
            "verified_events": verified_count,
            "total_events": len(events),
        }

    # Verify against external anchor (detect tail row deletion even if entire DB is rewritten)
    if ext_anchor is not None:
        target_head = expected_head_hash or ext_anchor.get("head_hash")
        ext_total = int(ext_anchor.get("total_events", 0))
        if len(events) < ext_total or expected_prev != target_head:
            return {
                "valid": False,
                "error": f"Tail deletion detected: chain ends at count {len(events)} with head '{expected_prev}', but external anchor records {ext_total} events with head '{ext_anchor.get('head_hash')}'.",
                "verified_events": verified_count,
                "total_events": len(events),
                "head_hash": expected_prev,
                "anchored_head_hash": ext_anchor.get("head_hash"),
            }

    # Fallback verification against internal anchor table if no external anchor is present
    anchor = (
        db.execute(select(AuditAnchor).order_by(AuditAnchor.created_at.desc())).scalars().first()
    )
    if anchor is not None and ext_anchor is None:
        target_head = expected_head_hash or anchor.head_hash
        if len(events) < anchor.total_events or expected_prev != target_head:
            return {
                "valid": False,
                "error": f"Tail deletion detected: chain ends at count {len(events)} with head '{expected_prev}', but anchor records {anchor.total_events} events with head '{anchor.head_hash}'.",
                "verified_events": verified_count,
                "total_events": len(events),
                "head_hash": expected_prev,
                "anchored_head_hash": anchor.head_hash,
            }

    return {
        "valid": True,
        "verified_events": verified_count,
        "total_events": len(events),
        "head_hash": expected_prev,
        "hash_schemes": scheme_counts,
    }
