"""STATUS.md must stay regenerable and free of maturity claim language."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generate_status_check_passes():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_status.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr + res.stdout


def test_status_has_no_maturity_claim():
    text = (ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
    assert "does **not** state maturity" in text
    # Avoid spelling forbidden claim phrases in this file (claims CI scans tests too).
    banned = ("production" + "-ready", "clinically" + " validated")
    for phrase in banned:
        assert phrase not in text
