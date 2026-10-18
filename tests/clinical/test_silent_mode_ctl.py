"""The silent-mode operator tool: freeze gate, exit codes, outcome import, no values in the report."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))
from vigil_api.shadow_store import ShadowPrediction, ShadowStore  # noqa: E402

SCRIPT = ROOT / "scripts" / "silent_mode_ctl.py"
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def run(*args, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT, env=env
    )


@pytest.fixture
def shadow(tmp_path):
    url = f"sqlite:///{tmp_path / 'shadow.db'}"
    store = ShadowStore(url)
    with store.session() as session:
        for i in range(80):
            session.add(
                ShadowPrediction(
                    patient_id=f"P{i % 8}", observation_id=f"o{i}", analyte_code="ca_15_3",
                    specimen_collected_at=T0 + timedelta(days=15 * i), canonical_value=1.0, score=0.1,
                    score_kind="m3_p_real", m3_action="explained", risk_tier="low",
                    would_alert=(i % 40 == 0), recorded_at=T0 + timedelta(days=15 * i),
                )
            )
        session.commit()
    store.dispose()
    return url


def test_real_use_is_refused_while_the_preregistration_is_not_frozen(shadow, tmp_path):
    assert not (ROOT / "docs" / "clinical" / "PREREG-FREEZE.json").exists()
    res = run("report", "--shadow-url", shadow, "--out", str(tmp_path / "out"))
    assert res.returncode == 4 and "not frozen" in res.stderr
    assert not (tmp_path / "out").exists()


def test_dry_run_requires_an_explicit_alert_budget(shadow, tmp_path):
    res = run("report", "--shadow-url", shadow, "--out", str(tmp_path / "out"), "--synthetic-dry-run")
    assert res.returncode != 0 and "alert-budget" in res.stderr


def test_dry_run_writes_a_labelled_report_and_exit_code_reflects_status(shadow, tmp_path):
    out = tmp_path / "out"
    res = run("report", "--shadow-url", shadow, "--out", str(out), "--synthetic-dry-run", "--alert-budget", "1000")
    # no outcomes imported: calibration is INSUFFICIENT, coverage NOT_MEASURABLE, nothing evaluable breaches
    assert res.returncode == 0, res.stderr
    md = (out / "silent_monitoring_report.md").read_text()
    assert md.startswith("> **REHEARSAL on unratified parameters.")
    data = json.loads((out / "silent_monitoring_report.json").read_text())
    assert data["parameters"]["PR-04_alert_budget_per_100_patient_months"] == 1000.0
    assert data["sections"]["alarm_rate"]["status"] == "OK"
    assert data["source"] == "shadow store only"


def test_a_breach_exits_3_and_is_reported(shadow, tmp_path):
    out = tmp_path / "out"
    res = run("report", "--shadow-url", shadow, "--out", str(out), "--synthetic-dry-run", "--alert-budget", "0.0001")
    assert res.returncode == 3, (res.returncode, res.stderr)
    assert json.loads((out / "silent_monitoring_report.json").read_text())["breach"] is True


def test_outcome_import_cli(shadow, tmp_path):
    csv_path = tmp_path / "outcomes.csv"
    csv_path.write_text(
        "patient_id,event_type,event_time\nP1,last_followup,2027-06-01\nGHOST,last_followup,2027-06-01\nP2,bogus,2027-06-01\n"
    )
    res = run("import-outcomes", "--shadow-url", shadow, "--csv", str(csv_path))
    assert res.returncode == 0, res.stderr
    report = json.loads(res.stdout)
    assert report["accepted"] == 1 and report["rejection_codes"] == {"BAD_ENUM": 1, "UNKNOWN_PATIENT": 1}
    assert "GHOST" not in res.stdout
