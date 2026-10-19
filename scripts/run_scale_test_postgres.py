#!/usr/bin/env python3
"""scripts/run_scale_test_postgres.py

Scale / latency probe against Postgres for MASTER_PLAN §9.5 budgets (G-03).

Plan budgets (do not reword):
  - 10^5 patients, 10^7 observations on a single Postgres instance with documented indexes
  - triage queue p95 < 400 ms
  - patient timeline p95 < 600 ms for 5-year history

Seeds a configurable cohort (defaults to a size this machine can finish honestly),
measures triage and timeline p95 via ASGI (same handlers as HTTP), and writes
reports/perf/SCALE_TEST_RESULTS.json. Never hand-edit that file.

Env:
  DATABASE_URL              postgresql+psycopg://...  (required; refuses sqlite)
  SCALE_N_PATIENTS          default 2000
  SCALE_OBS_PER_PATIENT     default 50
  SCALE_WARMUP              default 2
  SCALE_SAMPLES             default 30
  SCALE_SKIP_SEED           if true, skip reseeding
  SCALE_FORCE_HTTP=1        hit SCALE_API_BASE instead of in-process ASGI
  SCALE_API_BASE            default http://127.0.0.1:8000 (only with FORCE_HTTP)

Usage:
  DATABASE_URL=postgresql+psycopg://... uv run python scripts/run_scale_test_postgres.py
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "perf" / "SCALE_TEST_RESULTS.json"

PLAN_PATIENTS = 100_000
PLAN_OBSERVATIONS = 10_000_000
TRIAGE_P95_BUDGET_MS = 400.0
TIMELINE_P95_BUDGET_MS = 600.0


def _p95(samples: list[float]) -> float:
    if not samples:
        return float("nan")
    ordered = sorted(samples)
    idx = max(0, int(round(0.95 * (len(ordered) - 1))))
    return ordered[idx]


def main() -> int:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or db_url.startswith("sqlite"):
        print("DATABASE_URL must be a Postgres URL (postgresql+psycopg://...).", file=sys.stderr)
        return 2

    # Bind settings before any vigil_api import.
    os.environ["DATABASE_URL"] = db_url
    os.environ.setdefault("ENVIRONMENT", "local")
    os.environ.setdefault("REQUIRE_AUTH", "false")
    sys.path.insert(0, str(ROOT / "apps" / "api"))
    sys.path.insert(0, str(ROOT / "packages" / "vigil-ml"))
    sys.path.insert(0, str(ROOT / "packages" / "vigil-core"))

    from cryptography.fernet import Fernet

    if not os.environ.get("VIGIL_FIELD_ENCRYPTION_KEYS"):
        key = Fernet.generate_key().decode()
        os.environ["VIGIL_FIELD_ENCRYPTION_KEYS"] = key
        os.environ["FIELD_ENCRYPTION_KEYS"] = key

    n_patients = int(os.environ.get("SCALE_N_PATIENTS", "2000"))
    obs_per = int(os.environ.get("SCALE_OBS_PER_PATIENT", "50"))
    warmup = int(os.environ.get("SCALE_WARMUP", "2"))
    samples_n = int(os.environ.get("SCALE_SAMPLES", "30"))
    skip_seed = os.environ.get("SCALE_SKIP_SEED", "").lower() in {"1", "true", "yes"}
    force_http = os.environ.get("SCALE_FORCE_HTTP", "").lower() in {"1", "true", "yes"}
    api_base = os.environ.get("SCALE_API_BASE", "http://127.0.0.1:8000").rstrip("/")
    total_obs = n_patients * obs_per
    print(f"Scale probe: patients={n_patients} obs≈{total_obs}")

    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from vigil_api.database import Base, engine
    from vigil_api.models.patient import BaselineProfile, LabResult, Patient, RiskInference
    from vigil_api.models.v2 import (
        ConsentRecord,
        FollowUpTask,
        Observation,
        RiskAssessment,
    )

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for stmt in (
            "CREATE INDEX IF NOT EXISTS ix_observations_patient_specimen "
            "ON observations (patient_id, specimen_collected_at)",
            "CREATE INDEX IF NOT EXISTS ix_risk_assessments_patient_created "
            "ON risk_assessments (patient_id, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_status_patient_due "
            "ON follow_up_tasks (status, patient_id, due_date)",
            "CREATE INDEX IF NOT EXISTS ix_consent_records_patient_granted "
            "ON consent_records (patient_id, granted)",
        ):
            try:
                conn.execute(text(stmt))
            except Exception as exc:  # pragma: no cover
                print(f"index note: {exc}")

    Session = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)

    if not skip_seed:
        print("Seeding…")
        db = Session()
        try:
            for table in (
                "follow_up_tasks",
                "risk_assessments",
                "risk_inferences",
                "lab_results",
                "observations",
                "consent_records",
                "baseline_profiles",
                "patients",
            ):
                db.execute(text(f"DELETE FROM {table}"))
            db.commit()
            batch_o: list = []
            for i in range(n_patients):
                pid = f"SCALE-P-{i:06d}"
                # Commit the patient (and consent/baseline) before any of their observations
                # so Postgres FK checks succeed under batched inserts.
                db.add(
                    Patient(
                        id=pid,
                        age=45 + (i % 30),
                        status="active",
                        synthetic=True,
                        created_at=now - timedelta(days=365 * 5),
                        updated_at=now,
                    )
                )
                db.add(
                    ConsentRecord(
                        patient_id=pid,
                        granted=True,
                        scope="surveillance_monitoring",
                        granted_at=now - timedelta(days=365 * 5),
                    )
                )
                db.add(
                    BaselineProfile(
                        patient_id=pid,
                        tumor_stage=2,
                        er_status=True,
                        pr_status=True,
                        her2_status=False,
                        has_hypertension=False,
                        renal_history=False,
                        target_organ_susceptibility_vector={
                            "bone": 0.4,
                            "liver": 0.3,
                            "lung": 0.2,
                            "brain": 0.1,
                        },
                    )
                )
                db.flush()
                # The triage roster also reads the latest legacy inference, the latest risk assessment and
                # active follow-up tasks per patient; seed them so the probe measures the real work.
                lab = LabResult(
                    patient_id=pid,
                    date_drawn=(now - timedelta(days=i % 200)).replace(tzinfo=None),
                    alt_level=25.0,
                    ast_level=25.0,
                    creatinine=0.9,
                    ca_15_3=20.0 + (i % 40),
                    wbc_count=6.0,
                )
                db.add(lab)
                db.flush()
                db.add(
                    RiskInference(
                        patient_id=pid,
                        lab_result_id=lab.id,
                        calculated_metastasis_risk=((i * 37) % 100) / 100.0,
                        triage_flag=(i % 17 == 0),
                        justification_text="synthetic scale-probe inference",
                    )
                )
                db.add(
                    RiskAssessment(
                        patient_id=pid,
                        model_versions={"probe": "1"},
                        input_hash=f"probe-{i}",
                        score=((i * 53) % 100) / 100.0,
                        abstention=(i % 23 == 0),
                        uncertainty={"p_error": 0.05},
                    )
                )
                if i % 10 == 0:
                    db.add(
                        FollowUpTask(
                            patient_id=pid,
                            task_type="repeat_specimen",
                            due_date=now - timedelta(days=i % 20),
                        )
                    )
                for j in range(obs_per):
                    batch_o.append(
                        Observation(
                            id=str(uuid.uuid4()),
                            patient_id=pid,
                            analyte_code="ca_15_3",
                            value=20.0 + (j % 40),
                            unit="U/mL",
                            raw_value=20.0 + (j % 40),
                            raw_unit="U/mL",
                            specimen_collected_at=now - timedelta(days=30 * j),
                            result_received_at=now - timedelta(days=30 * j),
                            created_at=now - timedelta(days=30 * j),
                        )
                    )
                if len(batch_o) >= 2000:
                    db.add_all(batch_o)
                    db.commit()
                    batch_o = []
                elif (i + 1) % 100 == 0:
                    db.commit()
                if (i + 1) % 500 == 0:
                    print(f"  … {i + 1}/{n_patients} patients")
            if batch_o:
                db.add_all(batch_o)
            db.commit()
        finally:
            db.close()
        print("Seed complete.")

    import httpx
    from fastapi.testclient import TestClient

    triage_ms: list[float] = []
    timeline_ms: list[float] = []
    probe_patient = "SCALE-P-000000"

    if force_http:
        http_client = httpx.Client(base_url=api_base, timeout=120.0)
        mode = "http"

        def _get(path: str):
            return http_client.get(path)

        def _close() -> None:
            http_client.close()

    else:
        from vigil_api.main import app

        asgi_client = TestClient(app)
        mode = "asgi"

        def _get(path: str):
            return asgi_client.get(path)

        def _close() -> None:
            asgi_client.close()

    try:
        health = _get("/health")
        if health.status_code != 200:
            print(f"API /health failed: {health.status_code} {health.text}", file=sys.stderr)
            return 3

        for i in range(warmup + samples_n):
            t0 = time.perf_counter()
            r = _get("/api/v1/patients/triage")
            dt = (time.perf_counter() - t0) * 1000.0
            r.raise_for_status()
            if i >= warmup:
                triage_ms.append(dt)

            t0 = time.perf_counter()
            r2 = _get(f"/api/v1/patients/{probe_patient}/observations")
            dt2 = (time.perf_counter() - t0) * 1000.0
            r2.raise_for_status()
            if i >= warmup:
                timeline_ms.append(dt2)
    finally:
        _close()

    triage_p95 = _p95(triage_ms)
    timeline_p95 = _p95(timeline_ms)
    full_size = n_patients >= PLAN_PATIENTS and total_obs >= PLAN_OBSERVATIONS
    triage_ok = triage_p95 < TRIAGE_P95_BUDGET_MS
    timeline_ok = timeline_p95 < TIMELINE_P95_BUDGET_MS

    result = {
        "study": "SCALE_TEST_POSTGRES",
        "plan_budgets": {
            "patients": PLAN_PATIENTS,
            "observations": PLAN_OBSERVATIONS,
            "triage_p95_ms": TRIAGE_P95_BUDGET_MS,
            "timeline_p95_ms": TIMELINE_P95_BUDGET_MS,
        },
        "run": {
            "n_patients": n_patients,
            "obs_per_patient": obs_per,
            "approx_observations": total_obs,
            "full_plan_size": full_size,
            "warmup": warmup,
            "samples": samples_n,
            "client_mode": mode,
            "database": "postgres",
            "indexes": [
                "ix_observations_patient_specimen",
                "ix_risk_assessments_patient_created",
                "ix_follow_up_tasks_status_patient_due",
                "ix_consent_records_patient_granted",
            ],
            "machine": {
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "cpu_count": os.cpu_count(),
            },
            "command": (
                f"SCALE_N_PATIENTS={n_patients} SCALE_OBS_PER_PATIENT={obs_per} "
                "uv run python scripts/run_scale_test_postgres.py"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "metrics": {
            "triage_p50_ms": statistics.median(triage_ms) if triage_ms else None,
            "triage_p95_ms": triage_p95,
            "triage_samples_ms": [round(x, 3) for x in triage_ms],
            "timeline_p50_ms": statistics.median(timeline_ms) if timeline_ms else None,
            "timeline_p95_ms": timeline_p95,
            "timeline_samples_ms": [round(x, 3) for x in timeline_ms],
        },
        "verdicts": {
            "triage_p95_under_budget": triage_ok,
            "timeline_p95_under_budget": timeline_ok,
            "plan_size_reached": full_size,
            "honest_note": (
                "Full plan size (1e5 patients × ~1e7 observations) was not run on this machine; "
                "see run.n_patients / run.approx_observations. Budgets are unchanged."
                if not full_size
                else "Full plan size reached."
            ),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    # Keep one file per cohort size so scripts/analyze_scale_scaling.py can fit the scaling slope.
    runs_dir = OUT.parent / "scale_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"size_{n_patients}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "triage_p95_ms": triage_p95,
                "timeline_p95_ms": timeline_p95,
                "full_plan_size": full_size,
                "triage_ok": triage_ok,
                "timeline_ok": timeline_ok,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
