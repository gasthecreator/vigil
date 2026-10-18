#!/usr/bin/env python3
"""Gate: is docs/clinical/PREREGISTRATION.md frozen?

Frozen means all of:
  * docs/clinical/PREREG-FREEZE.json exists;
  * its prereg_sha256 equals the SHA-256 of the current PREREGISTRATION.md (any later edit breaks the freeze);
  * every parameter row (PR-xx) of section 7 has a ratification with a non-empty value, ratifier and date,
    and a row proposed with "no default" is not ratified with that placeholder;
  * no ratification refers to an unknown parameter;
  * its analysis_spec_sha256 equals the SHA-256 of docs/clinical/ANALYSIS-SPEC.md (the operational definitions the
    pre-registration leaves open are frozen together with it);
  * a bootstrap seed (integer) and a partition key identifier are recorded.

Exit 0 when frozen, 1 otherwise. Real-data evaluation entry points call `require_frozen()`.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "docs" / "clinical" / "PREREGISTRATION.md"
FREEZE = ROOT / "docs" / "clinical" / "PREREG-FREEZE.json"
SPEC = ROOT / "docs" / "clinical" / "ANALYSIS-SPEC.md"
ROW = re.compile(r"^\|\s*(PR-\d+)\s*\|(.*)$")


def parameters(text: str) -> dict[str, str]:
    """Parameter id -> proposed value cell, from the section 7 table."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            cells = [c.strip() for c in m.group(2).split("|")]
            out[m.group(1)] = cells[1] if len(cells) > 1 else ""
    return out


def check(
    prereg: Path | None = None, freeze: Path | None = None, spec: Path | None = None
) -> list[str]:
    spec = SPEC if spec is None else spec
    prereg = (
        PREREG if prereg is None else prereg
    )  # resolved at call time so tests can point the gate elsewhere
    freeze = FREEZE if freeze is None else freeze
    errs: list[str] = []
    if not prereg.exists():
        return [f"{prereg} is missing"]
    if not freeze.exists():
        return [f"freeze record {freeze.name} does not exist"]
    text = prereg.read_text(encoding="utf-8")
    try:
        rec = json.loads(freeze.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"freeze record is not valid JSON: {e}"]
    if rec.get("prereg_sha256") != hashlib.sha256(text.encode("utf-8")).hexdigest():
        errs.append(
            "prereg_sha256 does not match the current PREREGISTRATION.md (edited after the freeze, or wrong file)"
        )
    if not spec.exists():
        errs.append(f"{spec.name} is missing")
    elif (
        rec.get("analysis_spec_sha256")
        != hashlib.sha256(spec.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    ):
        errs.append(
            "analysis_spec_sha256 does not match the current ANALYSIS-SPEC.md (missing, edited after the freeze, or wrong file)"
        )
    if not isinstance(rec.get("bootstrap_seed"), int) or isinstance(
        rec.get("bootstrap_seed"), bool
    ):
        errs.append("bootstrap_seed must be an integer")
    if not str(rec.get("partition_key_id") or "").strip():
        errs.append("partition_key_id (identifier of the keyed-hash partition key) is missing")
    params = parameters(text)
    rat = {r.get("id"): r for r in rec.get("ratifications", [])}
    for pid, proposed in params.items():
        r = rat.get(pid)
        if r is None:
            errs.append(f"{pid} has no ratification")
            continue
        for field in ("value", "ratifier", "date"):
            if not str(r.get(field) or "").strip():
                errs.append(f"{pid}: ratification has empty {field}")
        if "no default" in proposed.lower() and "no default" in str(r.get("value", "")).lower():
            errs.append(f"{pid}: a value is required (the proposal had no default)")
    for pid in rat:
        if pid not in params:
            errs.append(f"{pid} is ratified but is not a parameter of PREREGISTRATION.md section 7")
    return errs


def require_frozen() -> None:
    errs = check()
    if errs:
        raise SystemExit(
            "PREREGISTRATION is NOT FROZEN; real-data evaluation is blocked:\n  - "
            + "\n  - ".join(errs)
        )


def main() -> int:
    errs = check()
    if errs:
        print("PREREGISTRATION is NOT FROZEN:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(
        "PREREGISTRATION is frozen: hash, ratifications, seed and partition key identifier verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
