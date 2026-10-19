"""Governance: i18n review-state ledger and glossary must stay honest."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_check_i18n_review_state_passes():
    cmd = [sys.executable, str(ROOT / "scripts" / "check_i18n_review_state.py")]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "i18n review-state OK" in res.stdout


def test_non_english_locales_are_unreviewed_in_ledger():
    import json

    review = json.loads((ROOT / "packages" / "ui" / "i18n" / "review_state.json").read_text())
    for loc in ("pcm", "yo", "ha", "ig"):
        assert review["locales"][loc]["status"] == "unreviewed"
        assert review["locales"][loc]["reviewed_by"] is None
