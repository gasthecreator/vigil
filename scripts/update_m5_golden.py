#!/usr/bin/env python3
"""Regenerate packages/vigil-ml/tests/golden/m5_golden.json (patient- and clinician-facing M5 wording).

Run ONLY after a deliberate wording change, and have the diff clinically reviewed: this file is what stops
patient-facing text from drifting silently. `uv run python scripts/update_m5_golden.py`
"""

from __future__ import annotations

import json
from pathlib import Path

from vigil_ml.m5 import generate_worked_journey, render_plain_language_explainer

OUT = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "vigil-ml"
    / "tests"
    / "golden"
    / "m5_golden.json"
)
JOURNEYS = ("j2_surprising_repeat", "false_alarm_explained", "real_progression_escalate")
VERDICTS = ("abstain", "explained", "needs_repeat", "escalate")


def build() -> dict:
    return {
        "explainer": {v: render_plain_language_explainer(v, synthetic=True) for v in VERDICTS},
        "journeys": {j: generate_worked_journey(j) for j in JOURNEYS},
    }


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
