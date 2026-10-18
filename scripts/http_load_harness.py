#!/usr/bin/env python3
"""scripts/http_load_harness.py

Real-network load harness for the Vigil API.

What is measured (and what is not)
  * The API runs as its own ``uvicorn`` OS process (1 worker, staging profile: authentication on,
    JWT secret and field-encryption keys freshly generated, database = a fresh SQLite file).
  * The client is a separate asyncio/httpx process-side loop talking to ``127.0.0.1:<port>`` over TCP.
    Latency is client-observed wall time per request (includes serialisation, TCP, the server's
    middleware, route, database and ML inference).
  * Closed-loop: ``concurrency`` workers each send the next request as soon as the previous finishes.
  * Server memory is the RSS of the uvicorn process sampled with ``ps`` (current RSS, not peak).
  * NOT measured: TLS, a reverse proxy, multiple server workers, PostgreSQL, a network between machines,
    or hospital hardware. Results describe this host, this SQLite file, one worker. ``host`` records the machine.

Results are written by the CLIs (run_load_test.py / run_soak_test.py) only; tests write to a tmp directory.
"""

from __future__ import annotations

import asyncio
import os
import platform
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PY_PATHS = [ROOT / "apps" / "api", *(ROOT / "packages" / p for p in ("vigil-core", "vigil-sim", "vigil-eval", "vigil-ml", "contracts"))]
FACILITY = "LOAD-FAC-01"
PATIENTS = [f"PAT-LOAD-{i:03d}" for i in range(10)]

# (method, path, weight). Writes go through the canonical ingestion pipeline (M3/K2/M5, alerts, audit chain).
WORKLOAD: list[tuple[str, str, int]] = [
    ("GET", "/health", 2),
    ("GET", "/api/v1/patients/", 3),
    ("GET", "/api/v1/patients/triage", 3),
    ("GET", "/api/v1/continuity/courses", 2),
    ("GET", "/api/v1/continuity/machines", 2),
    ("POST", "/api/v1/patients/{pid}/labs", 2),  # write path
]
# Provenance (kept honest): "p95_latency_ms" 200 for the whole mix is the target claimed by the Phase 8b report
# (PHASE-8B-REPORT errata E3), NOT a MASTER_PLAN section 9.5 figure. Section 9.5 gives "triage queue p95 < 400 ms"
# (at 10^5 patients on PostgreSQL; this harness has 10 patients on SQLite, so that row only bounds this setup).
BUDGETS = {"p95_latency_ms": 200.0, "error_rate_percent": 0.1, "triage_p95_ms": 400.0}
TRIAGE_PATH = "/api/v1/patients/triage"


def server_env(db_path: Path) -> dict[str, str]:
    from cryptography.fernet import Fernet

    env = {k: v for k, v in os.environ.items() if not k.startswith("VIGIL_")}
    env.update(
        ENVIRONMENT="staging",
        DATABASE_URL=f"sqlite:///{db_path}",
        JWT_SECRET_KEY=secrets.token_hex(32),
        VIGIL_FIELD_ENCRYPTION_KEYS=Fernet.generate_key().decode(),
        PYTHONPATH=os.pathsep.join(str(p) for p in PY_PATHS),
        PYTHONUNBUFFERED="1",
    )
    return env


def _provision() -> None:
    """Child-process entry: create schema, a facility, an admin and consented synthetic patients; print a token."""
    from vigil_api.auth import create_access_token
    from vigil_api.database import Base, SessionLocal, engine
    from vigil_api.models.v2 import ConsentRecord, Facility, Patient, User

    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    try:
        s.add(Facility(id=FACILITY, name="Load Test Facility", code="LTF-01"))
        s.add(User(id="USR-LOAD-ADMIN", username="load_admin", email="admin@loadtest.local", hashed_password="x", role="admin",
                   full_name="Load Admin", active=True, facility_id=FACILITY))
        for i, pid in enumerate(PATIENTS):
            s.add(Patient(id=pid, mrn=f"MRN-LOAD-{i:03d}", facility_id=FACILITY, age=52, primary_cancer_type="breast",
                          initial_stage="IIB", synthetic=True))
            s.add(ConsentRecord(id=f"CNS-LOAD-{i:03d}", patient_id=pid, consent_type="surveillance_monitoring",
                                granted=True, scope="direct_care"))
        s.commit()
    finally:
        s.close()
    print(create_access_token(subject="USR-LOAD-ADMIN", role="admin", facility_id=FACILITY))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def rss_mb(pid: int) -> float | None:
    r = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True)
    try:
        return round(int(r.stdout.strip()) / 1024.0, 2)
    except ValueError:
        return None


@contextmanager
def running_server():
    """Start uvicorn on a free port with a freshly provisioned database; yield (base_url, token, pid)."""
    with tempfile.TemporaryDirectory(prefix="vigil-load-") as td:
        env = server_env(Path(td) / "load.db")
        prov = subprocess.run([sys.executable, __file__, "--provision"], env=env, cwd=ROOT, capture_output=True, text=True)
        if prov.returncode != 0:
            raise RuntimeError(f"provisioning failed:\n{prov.stderr[-2000:]}")
        token = prov.stdout.strip().splitlines()[-1]
        port = _free_port()
        log = open(Path(td) / "server.log", "wb")
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "vigil_api.main:app", "--host", "127.0.0.1", "--port", str(port),
             "--workers", "1", "--log-level", "warning"],
            env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            deadline = time.time() + 90
            while time.time() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError("server exited early:\n" + (Path(td) / "server.log").read_text()[-2000:])
                try:
                    if httpx.get(base + "/health", timeout=2).status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(0.3)
            else:
                raise RuntimeError("server did not become healthy in 90 s")
            yield base, token, proc.pid
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
            log.close()


def _request_plan() -> list[tuple[str, str]]:
    plan = []
    for m, p, w in WORKLOAD:
        plan += [(m, p)] * w
    return plan


def _body(i: int) -> dict[str, Any]:
    r = np.random.default_rng(i)
    return {
        "alt_level": float(r.uniform(15, 45)), "ast_level": float(r.uniform(15, 45)),
        "creatinine": float(r.uniform(0.6, 1.2)), "ca_15_3": float(r.uniform(10, 30)),
        "wbc_count": float(r.uniform(4, 10)),
    }


async def _worker(wid: int, client: httpx.AsyncClient, counter: dict, stop_at: float | None, max_requests: int | None, rec: list):
    plan = _request_plan()
    while True:
        i = counter["n"]
        if (max_requests is not None and i >= max_requests) or (stop_at is not None and time.perf_counter() >= stop_at):
            return
        counter["n"] += 1
        method, path = plan[i % len(plan)]
        kwargs: dict[str, Any] = {}
        if "{pid}" in path:
            path = path.format(pid=PATIENTS[i % len(PATIENTS)])
            kwargs["json"] = _body(i)
        t0 = time.perf_counter()
        try:
            r = await client.request(method, path, **kwargs)
            status = r.status_code
        except httpx.HTTPError:
            status = 0
        rec.append((time.perf_counter(), path if "PAT-LOAD" not in path else "/api/v1/patients/{id}/labs", status, (time.perf_counter() - t0) * 1000.0))


def _stats(lats: list[float]) -> dict[str, float]:
    if not lats:
        return {}
    a = np.array(lats)
    return {"count": int(a.size), "p50_ms": round(float(np.percentile(a, 50)), 2), "p90_ms": round(float(np.percentile(a, 90)), 2),
            "p95_ms": round(float(np.percentile(a, 95)), 2), "p99_ms": round(float(np.percentile(a, 99)), 2),
            "mean_ms": round(float(a.mean()), 2), "max_ms": round(float(a.max()), 2)}


async def _drive(base: str, token: str, concurrency: int, max_requests: int | None, duration: float | None, sampler) -> tuple[list, float, list]:
    rec: list = []
    samples: list = []
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(base_url=base, headers={"Authorization": f"Bearer {token}"}, timeout=30.0, limits=limits) as client:
        t_start = time.perf_counter()
        stop_at = t_start + duration if duration else None
        counter = {"n": 0}
        workers = [asyncio.create_task(_worker(w, client, counter, stop_at, max_requests, rec)) for w in range(concurrency)]

        async def sample_loop():
            while True:
                await asyncio.sleep(sampler["interval"])
                samples.append({"elapsed_s": round(time.perf_counter() - t_start, 1), "rss_mb": rss_mb(sampler["pid"]), "requests": len(rec)})

        st = asyncio.create_task(sample_loop())
        await asyncio.gather(*workers)
        st.cancel()
        wall = time.perf_counter() - t_start
    return rec, wall, samples


def host_info() -> dict[str, Any]:
    return {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version(),
            "cpu_count": os.cpu_count(), "uvicorn_workers": 1, "database": "sqlite (single file)", "tls": False}


def run(concurrency: int, max_requests: int | None = None, duration_seconds: float | None = None, sample_interval: float = 5.0, label: str = "load") -> dict[str, Any]:
    assert (max_requests is None) != (duration_seconds is None), "give exactly one of max_requests / duration_seconds"
    with running_server() as (base, token, pid):
        warm = httpx.Client(base_url=base, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        for _, p, _w in WORKLOAD[:5]:
            warm.get(p)  # warm caches/model load outside the measured window
        warm.close()
        rss_start = rss_mb(pid)
        rec, wall, samples = asyncio.run(_drive(base, token, concurrency, max_requests, duration_seconds, {"pid": pid, "interval": sample_interval}))
        rss_end = rss_mb(pid)
    ok = lambda s: 200 <= s < 300  # noqa: E731
    lats = [r[3] for r in rec]
    failed = sum(1 for r in rec if not ok(r[2]))
    by_ep: dict[str, dict] = {}
    for ep in sorted({r[1] for r in rec}):
        sel = [r for r in rec if r[1] == ep]
        d = _stats([r[3] for r in sel])
        codes: dict[str, int] = {}
        for r in sel:
            codes[str(r[2])] = codes.get(str(r[2]), 0) + 1
        d["status_codes"] = codes
        by_ep[ep] = d
    overall = _stats(lats)
    err = 100.0 * failed / max(len(rec), 1)
    return {
        "test_name": f"Vigil API real-HTTP {label} test",
        "transport": "http",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": host_info(),
        "workload": [{"method": m, "path": p, "weight": w} for m, p, w in WORKLOAD],
        "concurrency": concurrency,
        "requested": {"max_requests": max_requests, "duration_seconds": duration_seconds},
        "total_requests": len(rec),
        "duration_seconds": round(wall, 2),
        "throughput_req_per_sec": round(len(rec) / wall, 2),
        "error_rate_percent": round(err, 4),
        "overall_latency": overall,
        "endpoints": by_ep,
        "server_rss_mb": {"start": rss_start, "end": rss_end, "samples": samples},
        "budgets": {
            "p95_latency_ms": {"measured": overall.get("p95_ms"), "budget": BUDGETS["p95_latency_ms"], "status": "PASS" if overall.get("p95_ms", 1e9) <= BUDGETS["p95_latency_ms"] else "FAIL"},
            "error_rate_percent": {"measured": round(err, 4), "budget": BUDGETS["error_rate_percent"], "status": "PASS" if err <= BUDGETS["error_rate_percent"] else "FAIL"},
            "triage_p95_ms": {"measured": by_ep.get(TRIAGE_PATH, {}).get("p95_ms"), "budget": BUDGETS["triage_p95_ms"], "status": "PASS" if by_ep.get(TRIAGE_PATH, {}).get("p95_ms", 1e9) <= BUDGETS["triage_p95_ms"] else "FAIL"},
        },
        "_records": rec,
    }


if __name__ == "__main__":
    if "--provision" in sys.argv:
        _provision()
    else:
        raise SystemExit("library module; use run_load_test.py / run_soak_test.py")
