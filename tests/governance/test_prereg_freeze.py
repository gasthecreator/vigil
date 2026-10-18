"""scripts/check_prereg_freeze.py: real-data evaluation is blocked until the pre-registration is frozen.

The check must be able to fail for every way a freeze can be incomplete or tampered with."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import check_prereg_freeze as cpf  # noqa: E402

PREREG = """# x
## 7. Decision parameters
| ID | Parameter | Proposed value | Rationale | Status |
|---|---|---|---|---|
| PR-01 | a | 0.80 | r | PROPOSED |
| PR-04 | budget | **no default** | r | PROPOSED (value required) |
"""


SPEC = "# analysis spec\ndefinitions\n"


def _freeze(prereg_text: str, **over) -> dict:
    rec = {
        "analysis_spec_sha256": hashlib.sha256(SPEC.encode()).hexdigest(),
        "prereg_sha256": hashlib.sha256(prereg_text.encode()).hexdigest(),
        "partition_key_id": "KEY-2027-01",
        "bootstrap_seed": 9001,
        "ratifications": [
            {
                "id": "PR-01",
                "value": "0.80",
                "ratifier": "Dr A (clinical lead)",
                "date": "2027-01-05",
            },
            {"id": "PR-04", "value": "3", "ratifier": "Dr A (clinical lead)", "date": "2027-01-05"},
        ],
    }
    rec.update(over)
    return rec


def _check(tmp_path, prereg_text=PREREG, rec=None, spec_text=SPEC):
    p, f = tmp_path / "PREREGISTRATION.md", tmp_path / "PREREG-FREEZE.json"
    s = tmp_path / "ANALYSIS-SPEC.md"
    p.write_text(prereg_text)
    s.write_text(spec_text)
    if rec is not None:
        f.write_text(json.dumps(rec))
    return cpf.check(p, f, s)


def test_complete_freeze_passes(tmp_path):
    assert _check(tmp_path, rec=_freeze(PREREG)) == []


def test_editing_the_analysis_spec_after_the_freeze_fails(tmp_path):
    errs = _check(tmp_path, rec=_freeze(PREREG), spec_text=SPEC + "one more definition\n")
    assert any("analysis_spec_sha256" in e for e in errs)


def test_freeze_without_an_analysis_spec_hash_fails(tmp_path):
    rec = _freeze(PREREG)
    del rec["analysis_spec_sha256"]
    assert any("analysis_spec_sha256" in e for e in _check(tmp_path, rec=rec))


def test_missing_freeze_record_fails(tmp_path):
    errs = _check(tmp_path, rec=None)
    assert any("freeze record" in e for e in errs)


def test_any_edit_after_freeze_fails_the_hash(tmp_path):
    rec = _freeze(PREREG)
    errs = _check(tmp_path, prereg_text=PREREG + "\nedited\n", rec=rec)
    assert any("sha256" in e.lower() for e in errs)


@pytest.mark.parametrize("drop", ["PR-01", "PR-04"])
def test_unratified_parameter_fails(tmp_path, drop):
    rec = _freeze(PREREG)
    rec["ratifications"] = [r for r in rec["ratifications"] if r["id"] != drop]
    assert any(drop in e for e in _check(tmp_path, rec=rec))


def test_ratification_without_named_ratifier_or_date_or_value_fails(tmp_path):
    for field in ("ratifier", "date", "value"):
        rec = _freeze(PREREG)
        rec["ratifications"][0][field] = ""
        assert any("PR-01" in e for e in _check(tmp_path, rec=rec)), field


def test_value_required_row_cannot_be_ratified_with_the_placeholder(tmp_path):
    rec = _freeze(PREREG)
    rec["ratifications"][1]["value"] = "no default"
    assert any("PR-04" in e for e in _check(tmp_path, rec=rec))


def test_missing_seed_or_key_identifier_fails(tmp_path):
    assert any("seed" in e for e in _check(tmp_path, rec=_freeze(PREREG, bootstrap_seed=None)))
    assert any("partition" in e for e in _check(tmp_path, rec=_freeze(PREREG, partition_key_id="")))


def test_unknown_parameter_in_freeze_is_rejected(tmp_path):
    rec = _freeze(PREREG)
    rec["ratifications"].append(
        {"id": "PR-99", "value": "1", "ratifier": "x", "date": "2027-01-05"}
    )
    assert any("PR-99" in e for e in _check(tmp_path, rec=rec))


def test_repository_state_is_not_frozen_and_the_cli_exits_nonzero():
    """On this branch there is no freeze record: the gate must say so."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_prereg_freeze.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert r.returncode == 1 and "NOT FROZEN" in r.stdout
