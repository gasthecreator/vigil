"""Silent mode (PREREGISTRATION section 6, tier T-Q), tested over HTTP.

Invariants:
1. In silent mode every ingestion route (all six) sends model output to a separate shadow database and returns
   none; the clinical database receives no RiskAssessment, Alert, FollowUpTask or RiskInference row.
2. No request field, header or query parameter can switch silent mode off, and no route toggles or reads it.
3. After ingestion, no GET route returns any shadow value, as any role.
4. Routes whose response is itself a model output are blocked (HTTP 409).
5. The mode fails closed: with no usable shadow store the request is refused and nothing is committed.
6. Data-quality rejections (unit errors, hazard H4) are still reported in silent mode.
7. The shadow store cannot be reached from clinician-facing code (import rule) and is not in the clinical database.
"""

from __future__ import annotations

import ast
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session
from vigil_api import shadow_store, silent_mode
from vigil_api.config import settings
from vigil_api.main import app
from vigil_api.models.patient import RiskInference
from vigil_api.models.v2 import (
    Alert,
    AlertAcknowledgement,
    AuditEvent,
    FollowUpTask,
    Observation,
    RiskAssessment,
)
from vigil_api.shadow_store import ShadowDetectorState, ShadowPrediction

SERIES = [20.1, 20.4, 19.8, 20.2, 21.0, 80.0, 95.0]
API_DIR = Path(__file__).resolve().parents[1] / "vigil_api"
ROLES = ["clinician", "nurse_clerk", "quality_lead", "admin", "patient", "caregiver"]


def _time(i: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=70) + timedelta(days=7 * i)


# --- the six ingestion routes: each returns (response, number_of_values_sent) -------------------------------


def ingest_observations(env, pid, i, value, headers):
    return env.client.post(
        f"/api/v1/patients/{pid}/observations",
        json={
            "analyte_code": "ca_15_3", "value": value, "unit": "U/mL",
            "specimen_collected_at": _time(i).isoformat(),
        },
        headers=headers,
    )


def ingest_legacy_labs(env, pid, i, value, headers):
    return env.client.post(
        f"/api/v1/patients/{pid}/labs",
        json={
            "date_drawn": _time(i).isoformat(), "alt_level": 25.0, "ast_level": 25.0,
            "creatinine": 0.9, "ca_15_3": value, "wbc_count": 6.0,
        },
        headers=headers,
    )


def ingest_batch(env, pid, i, value, headers):
    csv = (
        "patient_id,analyte_code,value,unit,specimen_collected_at\n"
        f"{pid},ca_15_3,{value},U/mL,{_time(i).isoformat()}\n"
    )
    return env.client.post(
        "/api/v1/observations/batch-import", content=csv.encode(),
        headers={**headers, "content-type": "text/csv"},
    )


def ingest_hl7(env, pid, i, value, headers):
    stamp = _time(i).strftime("%Y%m%d%H%M%S")
    msg = (
        f"MSH|^~\\&|LIS|HOSP|VIGIL|ONC|{stamp}||ORU^R01|MSG-{pid[:6]}-{i}|P|2.5\r\n"
        f"PID|1||{pid}^^^HOSP^MR||Doe^Jane\r\n"
        f"OBR|1|||LAB^SURVEILLANCE|||{stamp}\r\n"
        f"OBX|1|NM|83082-8^CA 15-3^LN||{value}|U/mL|< 30.0|N|||F|||{stamp}|LAB-01\r\n"
    )
    return env.client.post(
        "/api/v1/hl7/oru-r01", content=msg.encode(), headers={**headers, "content-type": "text/plain"}
    )


def ingest_fhir(env, pid, i, value, headers):
    return env.client.post(
        "/api/v1/fhir/Observation",
        json={
            "resourceType": "Observation", "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "83082-8", "display": "CA 15-3"}]},
            "subject": {"reference": f"Patient/{pid}"},
            "effectiveDateTime": _time(i).isoformat(),
            "valueQuantity": {"value": value, "unit": "U/mL", "system": "http://unitsofmeasure.org", "code": "U/mL"},
        },
        headers=headers,
    )


def ingest_sync(env, pid, i, value, headers):
    t = _time(i).isoformat()
    return env.client.post(
        "/api/v1/sync/batch",
        json={
            "sync_id": f"S-{pid[:6]}-{i}", "client_device_id": "tab", "client_timestamp": t,
            "mutations": [{
                "client_mutation_id": f"m-{pid[:6]}-{i}", "entity_type": "observation", "action": "create",
                "patient_id": pid, "client_updated_at": t,
                "payload": {"analyte_code": "ca_15_3", "value": value, "unit": "U/mL", "specimen_collected_at": t},
            }],
        },
        headers=headers,
    )


INGESTORS = {
    "observations": ingest_observations,
    "legacy_labs": ingest_legacy_labs,
    "batch_import": ingest_batch,
    "hl7": ingest_hl7,
    "fhir": ingest_fhir,
    "sync": ingest_sync,
}


def shadow_rows(env):
    store = shadow_store.get_store(env.shadow_url)
    with store.session() as session:
        return session.execute(select(ShadowPrediction).order_by(ShadowPrediction.specimen_collected_at)).scalars().all()


def clinical_output_counts(env):
    with Session(env.engine) as session:
        return {
            model.__name__: session.execute(select(func.count()).select_from(model)).scalar_one()
            for model in (RiskAssessment, Alert, FollowUpTask, RiskInference, AlertAcknowledgement)
        }


def run_series(env, name, pid, role="clinician"):
    headers = env.headers(role)
    responses = []
    for i, value in enumerate(SERIES):
        res = INGESTORS[name](env, pid, i, value, headers)
        assert res.status_code in (200, 201, 202), f"{name} #{i}: {res.status_code} {res.text}"
        responses.append(res)
    return responses


# --- 1. diversion on every route, as every role allowed to ingest ---------------------------------------


@pytest.mark.parametrize("route", sorted(INGESTORS))
@pytest.mark.parametrize("role", ["clinician", "nurse_clerk", "admin"])
def test_ingestion_diverts_outputs_to_the_shadow_store(api_env, monkeypatch, route, role):
    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient(f"MRN-S-{route}-{role}")
    responses = run_series(env, route, pid, role)

    # Nothing model-derived in any response body.
    for res in responses:
        text = res.text
        for forbidden in ("escalate", "needs_repeat", "biomarker_spike", "lab_error_repeat", "clinical_note"):
            assert forbidden not in text, f"{route}: '{forbidden}' in a silent-mode response"
    if route == "observations":
        body = responses[-1].json()
        assert body["risk_assessment"] is None and body["alert"] is None and body["follow_up_task"] is None
        assert body["outputs_withheld"] is True
        assert body["adjudicated_action"] == silent_mode.WITHHELD_ACTION

    # The clinical database holds the data but no outputs.
    assert clinical_output_counts(env) == {k: 0 for k in clinical_output_counts(env)}
    with Session(env.engine) as session:
        per_draw = 5 if route == "legacy_labs" else 1
        assert session.execute(select(func.count()).select_from(Observation)).scalar_one() == len(SERIES) * per_draw

    # The shadow store holds one prediction per value, and the spike is a would-alert.
    rows = shadow_rows(env)
    ca = [r for r in rows if r.analyte_code == "ca_15_3"]
    assert len(ca) == len(SERIES)
    assert ca[-1].would_alert is True and ca[-1].m3_action == "escalate"
    assert all(r.score_kind == "m3_p_real" for r in rows)


def test_audit_log_carries_no_model_output_in_silent_mode(api_env, monkeypatch):
    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient("MRN-S-audit")
    run_series(env, "observations", pid)
    with Session(env.engine) as session:
        events = session.execute(select(AuditEvent).where(AuditEvent.action == "observation.ingest")).scalars().all()
    assert len(events) == len(SERIES)
    for event in events:
        assert "action" not in event.details and "has_alert" not in event.details
        assert event.details.get("silent_mode") is True


def test_silent_mode_matches_normal_mode_model_outputs(api_env, monkeypatch):
    """The shadow store records exactly what the normal pipeline would have produced (no divergence)."""
    env = api_env
    pid_n = env.create_patient("MRN-S-normal")
    normal = [r.json() for r in run_series(env, "observations", pid_n)]
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid_s = env.create_patient("MRN-S-silent")
    run_series(env, "observations", pid_s)
    rows = shadow_rows(env)
    assert len(rows) == len(SERIES)
    for res, row in zip(normal, rows):
        assert row.m3_action == res["adjudicated_action"]
        assert row.score == pytest.approx(res["risk_assessment"]["score"], rel=1e-9, abs=1e-12)
        assert row.would_alert == (res["alert"] is not None)
        assert row.risk_tier == res["risk_assessment"]["risk_tier"]


def test_detector_state_lives_in_the_shadow_store_only(api_env, monkeypatch):
    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient("MRN-S-k2")
    run_series(env, "observations", pid)
    from vigil_api.models.v2 import Patient

    with Session(env.engine) as session:
        assert session.get(Patient, pid).detector_state is None
    with shadow_store.get_store(env.shadow_url).session() as session:
        state = session.get(ShadowDetectorState, pid)
        assert state is not None and len(state.state["history"]) == len(SERIES)


# --- 2. forged requests cannot switch it off --------------------------------------------------------------


@pytest.mark.parametrize(
    "tamper",
    [
        {"json_extra": {"silent_mode": False, "silent": False, "SILENT_MODE": False}},
        {"headers": {"X-Vigil-Silent-Mode": "false", "X-Silent-Mode": "0", "X-Vigil-Role": "admin"}},
        {"params": {"silent_mode": "false", "silent": "0", "debug": "1"}},
    ],
    ids=["forged-body", "forged-headers", "forged-query"],
)
def test_forged_requests_cannot_disable_silent_mode(api_env, monkeypatch, tamper):
    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient("MRN-S-forge")
    base = {"analyte_code": "ca_15_3", "value": 95.0, "unit": "U/mL"}
    res = env.client.post(
        f"/api/v1/patients/{pid}/observations",
        json={**base, **tamper.get("json_extra", {})},
        headers={**env.headers("clinician"), **tamper.get("headers", {})},
        params=tamper.get("params"),
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["risk_assessment"] is None and body["outputs_withheld"] is True
    assert clinical_output_counts(env)["RiskAssessment"] == 0


def test_no_route_toggles_or_reads_silent_state():
    paths = list(app.openapi()["paths"])
    assert not [p for p in paths if re.search(r"silent|shadow", p, re.I)], paths
    schema_text = str(app.openapi())
    assert "shadow_predictions" not in schema_text


# --- 3. nothing from the shadow store is readable through any GET route, as any role ---------------------


def _fill(path: str, pid: str, obs_id: str) -> str:
    return (
        path.replace("{id}", pid).replace("{obs_id}", obs_id).replace("{alert_id}", "x")
        .replace("{task_id}", "x").replace("{share_id}", "x").replace("{share_token}", "cg_x")
    )


def test_no_get_route_returns_a_shadow_value_as_any_role(api_env, monkeypatch):
    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient("MRN-S-leak")
    for name in ("observations", "hl7"):
        run_series(env, name, pid)
    rows = shadow_rows(env)
    assert rows
    with Session(env.engine) as session:
        obs_id = session.execute(select(Observation.id).limit(1)).scalar_one()

    markers = {r.id for r in rows}
    markers |= {f"{r.score!r}"[:10] for r in rows if r.score > 1e-3}  # score digits (skip tiny values)
    markers |= {"biomarker_spike", "lab_error_repeat", "sequential_divergence", "critical_panic_boundary"}

    get_paths = [p for p, ops in app.openapi()["paths"].items() if "get" in ops]
    assert len(get_paths) >= 20
    leaks = []
    for role in ROLES + ["unauthenticated"]:
        headers = {} if role == "unauthenticated" else env.headers(
            role, subject=pid if role == "patient" else None,
            patient_id=pid if role in ("patient", "caregiver") else None,
        )
        for path in get_paths:
            url = _fill(path, pid, obs_id)
            if "alerts/stream" in url:
                url += f"?patient_id={pid}"
            res = env.client.get(url, headers=headers)
            for marker in markers:
                if marker in res.text:
                    leaks.append(f"{role} GET {path}: contains {marker!r}")
    assert leaks == [], "\n".join(leaks[:20])


# --- 4. blocked routes ------------------------------------------------------------------------------------


def test_routes_whose_response_is_model_output_are_blocked(api_env, monkeypatch):
    env = api_env
    pid = env.create_patient("MRN-S-block")
    baseline = {"tumor_stage": 2, "er_status": True, "pr_status": True, "her2_status": False}
    ok = env.client.post(f"/api/v1/patients/{pid}/baseline", json=baseline, headers=env.headers("clinician"))
    assert ok.status_code == 200
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    blocked = env.client.post(f"/api/v1/patients/{pid}/baseline", json=baseline, headers=env.headers("clinician"))
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == silent_mode.BLOCKED_CODE
    sim = env.client.post(
        f"/api/v1/patients/{pid}/simulate", json={"hypothetical_lab": {"ca_15_3": 50.0}},
        headers=env.headers("clinician"),
    )
    assert sim.status_code == 409 and sim.json()["detail"]["code"] == silent_mode.BLOCKED_CODE
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    seed = env.client.post("/api/v1/analytics/seed-demo-cohort", headers=env.headers("admin"))
    assert seed.status_code == 409


# --- 5. fail closed ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad_url", ["", "clinical"], ids=["unset", "same-as-clinical"])
def test_ingestion_fails_closed_without_a_separate_shadow_store(api_env, monkeypatch, bad_url):
    env = api_env
    pid = env.create_patient("MRN-S-closed")
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    monkeypatch.setattr(settings, "SILENT_SHADOW_DATABASE_URL", settings.DATABASE_URL if bad_url else "")
    res = ingest_observations(env, pid, 0, 20.0, env.headers("clinician"))
    assert res.status_code == 503, res.text
    with Session(env.engine) as session:
        assert session.execute(select(func.count()).select_from(Observation)).scalar_one() == 0
    assert clinical_output_counts(env)["RiskAssessment"] == 0


def test_settings_refuse_unsafe_silent_configuration(monkeypatch):
    from vigil_api.config import Settings

    monkeypatch.setenv("VIGIL_SILENT_MODE", "true")
    monkeypatch.delenv("VIGIL_SILENT_SHADOW_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="SHADOW_DATABASE_URL"):
        Settings(SILENT_MODE=True, SILENT_SHADOW_DATABASE_URL="")
    with pytest.raises(ValueError, match="must differ"):
        Settings(SILENT_MODE=True, DATABASE_URL="sqlite:///x.db", SILENT_SHADOW_DATABASE_URL="sqlite:///x.db")
    Settings(SILENT_MODE=True, DATABASE_URL="sqlite:///x.db", SILENT_SHADOW_DATABASE_URL="sqlite:///y.db")


# --- 6. data-quality rejection is not suppressed ----------------------------------------------------------


def test_unit_errors_are_still_rejected_in_silent_mode(api_env, monkeypatch):
    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient("MRN-S-units")
    res = env.client.post(
        f"/api/v1/patients/{pid}/observations",
        json={"analyte_code": "ca_15_3", "value": 20.0, "unit": "mmol/L"},
        headers=env.headers("clinician"),
    )
    assert res.status_code == 422
    assert shadow_rows(env) == []


# --- 7. structure: the clinician-facing code cannot read the shadow store ---------------------------------


def _imported_modules(path: Path) -> set:
    tree = ast.parse(path.read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            found.add(base)
            found |= {f"{base}.{a.name}" for a in node.names}
    return found


def test_only_the_write_facade_and_the_monitor_import_the_shadow_store():
    offenders = []
    for path in API_DIR.rglob("*.py"):
        if path.name in ("shadow_store.py", "silent_mode.py", "silent_monitoring.py"):
            continue
        mods = _imported_modules(path)
        if any(m.startswith("vigil_api.shadow_store") or m.endswith("shadow_store") for m in mods) or any(
            m.startswith("vigil_api.silent_monitoring") for m in mods
        ):
            offenders.append(str(path.relative_to(API_DIR)))
    assert offenders == [], f"modules importing the shadow store or monitor: {offenders}"


def test_endpoint_modules_use_only_the_declared_silent_mode_api():
    allowed = set(silent_mode.PUBLIC_API)
    used = set()
    for path in (API_DIR / "api").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "silent_mode":
                used.add(node.attr)
    assert used, "endpoint modules should reference silent_mode"
    assert used <= allowed, f"undeclared silent_mode attributes used: {used - allowed}"
    # The facade has no function that returns predictions or outcomes.
    public = {n for n in dir(silent_mode) if not n.startswith("_")}
    readers = [n for n in public if re.search(r"^(read|get|list|fetch|query|load)_(pred|outcome|shadow)", n)]
    assert readers == []


def test_shadow_tables_are_not_in_the_clinical_database(api_env, monkeypatch):
    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient("MRN-S-iso")
    run_series(env, "observations", pid)
    clinical_tables = set(inspect(env.engine).get_table_names())
    assert not [t for t in clinical_tables if t.startswith("shadow_")]
    shadow_tables = set(inspect(shadow_store.get_store(env.shadow_url).engine).get_table_names())
    assert {"shadow_predictions", "shadow_detector_states", "shadow_outcomes"} <= shadow_tables
    assert not (shadow_tables & clinical_tables)


# --- leakage attacks: try to reach the shadow store through clinician-facing inputs ---------------------


ATTACKS = [
    "x' UNION SELECT id,patient_id,m3_action FROM shadow_predictions --",
    "'; ATTACH DATABASE '/tmp/shadow.db' AS s; --",
    "1 OR 1=1",
    "../../shadow.db",
    "%00",
]


@pytest.mark.parametrize("attack", ATTACKS)
def test_injection_through_query_parameters_cannot_reach_the_shadow_store(api_env, monkeypatch, attack):
    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient("MRN-S-attack")
    run_series(env, "observations", pid)
    rows = shadow_rows(env)
    ids = {r.id for r in rows}
    for headers in (env.headers("clinician"), env.headers("admin"), env.headers("quality_lead")):
        for url, params in [
            ("/api/v1/alerts/", {"status_filter": attack}),
            ("/api/v1/alerts/", {"skip": attack, "limit": attack}),
            ("/api/v1/patients/", {"mrn": attack, "search": attack}),
            ("/api/v1/audit/events", {"action": attack, "resource_id": attack}),
            ("/api/v1/continuity/ledger", {"patient_id": attack}),
        ]:
            res = env.client.get(url, params=params, headers=headers)
            assert res.status_code < 500, f"{url} {params}: {res.status_code}"
            assert not any(i in res.text for i in ids)
            if res.status_code == 200:
                assert "m3_action" not in res.text and "k2_log_e" not in res.text


# --- the monitor works on what the pipeline really wrote ---------------------------------------------------


def test_monitor_reads_what_the_pipeline_wrote(api_env, monkeypatch):
    from vigil_api import silent_monitoring as sm

    env = api_env
    monkeypatch.setattr(settings, "SILENT_MODE", True)
    pid = env.create_patient("MRN-S-monitor")
    run_series(env, "observations", pid)
    bad = env.client.post(
        f"/api/v1/patients/{pid}/observations",
        json={"analyte_code": "ca_15_3", "value": 20.0, "unit": "mmol/L"},
        headers=env.headers("clinician"),
    )
    assert bad.status_code == 422
    unknown = env.client.post(
        f"/api/v1/patients/{pid}/observations",
        json={"analyte_code": "not_an_analyte", "value": 1.0, "unit": "U/L"},
        headers=env.headers("clinician"),
    )
    assert unknown.status_code == 422

    store = shadow_store.get_store(env.shadow_url)
    params = sm.Parameters(
        slope_low=0.8, slope_high=1.2, alert_budget=1000.0, min_window=3,
        coverage_shortfall=0.05, provenance="integration test (not ratified)",
    )
    rep = sm.build_report(store, params)
    assert rep["data"]["predictions"] == len(SERIES)
    assert rep["data"]["landmarks"] == len(SERIES)
    assert rep["data"]["rejections"] == 2
    assert rep["sections"]["alarm_rate"]["alerts"] >= 1
    assert rep["data"]["score_kinds"] == ["m3_p_real"]
    imported = sm.import_outcomes(
        store,
        [{"patient_id": pid, "event_type": "last_followup", "event_time": (datetime.now(timezone.utc) + timedelta(days=400)).isoformat()}],
        source="integration-test",
    )
    assert imported["accepted"] == 1
    again = sm.build_report(store, params)
    assert again["data"]["patients_with_outcomes"] == 1
