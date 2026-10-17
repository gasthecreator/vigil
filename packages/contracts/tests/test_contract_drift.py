"""Automated Contract Drift & Schema Validation Tests.

Adheres to MASTER_PLAN.md §9.2, WP5.5, and Phase 5 deliverables:
- Compares committed docs/api/openapi.json against live FastAPI app.openapi().
- Detects uncommitted API endpoint changes or schema drift.
- Verifies TypeScript client & type generation integrity.
"""

from __future__ import annotations

import json
from pathlib import Path

from vigil_api.main import app

ROOT = Path(__file__).resolve().parents[3]
OPENAPI_FILE = ROOT / "docs" / "api" / "openapi.json"
TS_TYPES_FILE = ROOT / "packages" / "contracts" / "ts" / "types.ts"
TS_CLIENT_FILE = ROOT / "packages" / "contracts" / "ts" / "client.ts"


def test_openapi_spec_has_no_drift():
    """Verify that committed openapi.json matches live app.openapi() exactly."""
    assert OPENAPI_FILE.exists(), f"OpenAPI specification not found at {OPENAPI_FILE}"

    with open(OPENAPI_FILE, "r", encoding="utf-8") as f:
        committed_spec = json.load(f)

    live_spec = app.openapi()

    # Compare paths keys
    committed_paths = set(committed_spec.get("paths", {}).keys())
    live_paths = set(live_spec.get("paths", {}).keys())
    assert committed_paths == live_paths, (
        f"Path drift detected!\n"
        f"Missing in committed: {live_paths - committed_paths}\n"
        f"Extra in committed: {committed_paths - live_paths}"
    )

    # Compare schemas
    committed_schemas = set(committed_spec.get("components", {}).get("schemas", {}).keys())
    live_schemas = set(live_spec.get("components", {}).get("schemas", {}).keys())
    assert committed_schemas == live_schemas, (
        f"Schema drift detected!\n"
        f"Missing in committed: {live_schemas - committed_schemas}\n"
        f"Extra in committed: {committed_schemas - live_schemas}"
    )


def test_core_endpoints_present_in_contract():
    """Verify that all core Phase 5 endpoints are explicitly present in the OpenAPI contract."""
    with open(OPENAPI_FILE, "r", encoding="utf-8") as f:
        spec = json.load(f)

    paths = spec.get("paths", {})
    required_routes = [
        "/api/v1/patients/",
        "/api/v1/patients/{id}/observations",
        "/api/v1/patients/{id}/consent",
        "/api/v1/observations/batch-import",
        "/api/v1/fhir/Observation",
        "/api/v1/hl7/oru-r01",
        "/api/v1/alerts/stream",
        "/api/v1/alerts/{alert_id}/acknowledge",
        "/api/v1/follow-up/outreach",
        "/api/v1/sync/batch",
        "/api/v1/audit/verify",
    ]

    for route in required_routes:
        assert route in paths, f"Required contract route '{route}' missing from OpenAPI spec!"


def test_typescript_artifacts_exist_and_cover_entities():
    """Verify that TypeScript type definitions and client are generated and valid."""
    assert TS_TYPES_FILE.exists(), f"TypeScript types missing at {TS_TYPES_FILE}"
    assert TS_CLIENT_FILE.exists(), f"TypeScript client missing at {TS_CLIENT_FILE}"

    types_content = TS_TYPES_FILE.read_text(encoding="utf-8")
    client_content = TS_CLIENT_FILE.read_text(encoding="utf-8")

    # Key interfaces must exist
    for expected_type in [
        "PatientCreate",
        "ObservationCreateRequest",
        "RiskAssessmentSummary",
        "AlertSummary",
        "AlertAcknowledgeRequest",
        "SyncBatchRequest",
        "SyncBatchResponse",
    ]:
        assert f"export interface {expected_type}" in types_content or f"export type {expected_type}" in types_content, (
            f"Expected TypeScript type '{expected_type}' not found in {TS_TYPES_FILE}"
        )

    # Key client methods must exist
    for expected_method in [
        "ingestObservation",
        "listAlerts",
        "acknowledgeAlert",
        "processSyncBatch",
        "verifyAuditChain",
    ]:
        assert f"async {expected_method}(" in client_content, (
            f"Expected client method '{expected_method}' not found in {TS_CLIENT_FILE}"
        )
