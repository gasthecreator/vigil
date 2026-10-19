"""Alert rules must link real runbooks and reference metrics that the API actually exports (G-09)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "infra" / "prometheus" / "alerts.yml"
EXTERNAL_METRICS = {"probe_success"}  # from blackbox_exporter, not from the API


def _alerts(text: str | None = None) -> list[dict]:
    doc = yaml.safe_load(text if text is not None else RULES.read_text(encoding="utf-8"))
    return [r for g in doc["groups"] for r in g["rules"]]


def problems(alerts: list[dict]) -> list[str]:
    exported = set(
        re.findall(r'"(vigil_[a-z_]+)"', (ROOT / "apps/api/vigil_api/observability.py").read_text())
    )
    exported |= {m + s for m in list(exported) for s in ("_bucket", "_sum", "_count")}
    out = []
    for a in alerts:
        runbook = a["annotations"].get("runbook_url", "")
        if not (ROOT / runbook).is_file():
            out.append(f"{a['alert']}: runbook_url {runbook!r} does not exist")
        for metric in set(re.findall(r"\b((?:vigil|probe)_[a-z_]+)", a["expr"])):
            if metric not in exported and metric not in EXTERNAL_METRICS:
                out.append(f"{a['alert']}: metric {metric} is not exported by the API")
    return out


def test_alert_rules_are_well_formed_and_real():
    alerts = _alerts()
    assert len(alerts) >= 3
    assert problems(alerts) == []


def test_alert_check_fails_on_phantom_metric_and_missing_runbook():
    bad = _alerts(
        """
groups:
  - name: x
    rules:
      - alert: Phantom
        expr: vigil_queue_depth_total > 5
        annotations: { runbook_url: docs/runbooks/DOES_NOT_EXIST.md }
"""
    )
    found = problems(bad)
    assert any("not exported" in p for p in found) and any("does not exist" in p for p in found)
