"""HMAC attestation for reports produced by the silent shadow-store monitor."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from vigil_api.config import settings


def _canonical(report: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in report.items() if key != "governance_attestation"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def attest_monitor_report(report: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with a secret-key MAC so admin clients cannot fabricate monitor alarms."""
    body = {key: value for key, value in report.items() if key != "governance_attestation"}
    digest = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), _canonical(body), hashlib.sha256).hexdigest()
    return {**body, "governance_attestation": {"algorithm": "HMAC-SHA256", "signature": digest}}


def verify_monitor_report(report: dict[str, Any]) -> bool:
    token = report.get("governance_attestation")
    if not isinstance(token, dict) or token.get("algorithm") != "HMAC-SHA256":
        return False
    supplied = token.get("signature")
    if not isinstance(supplied, str):
        return False
    expected = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), _canonical(report), hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)
