#!/usr/bin/env python3
"""Licence allowlist gate (G-07).

Fails only on short SPDX / classifier identifiers that are incompatible with
Apache-2.0 redistribution (AGPL/GPL-3/SSPL/BUSL/Commons-Clause). Long licence
*texts* are not substring-scanned (they contain warranty language that false-triggers).

Usage:
  uv run python scripts/check_licences.py
  uv run python scripts/check_licences.py --seed-fail
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "quality" / "LICENCE_CHECK.json"

FORBIDDEN_SPDX = {
    "gpl-3.0",
    "gpl-3.0-only",
    "gpl-3.0-or-later",
    "gplv3",
    "agpl-3.0",
    "agpl-3.0-only",
    "agpl-3.0-or-later",
    "agplv3",
    "sspl-1.0",
    "busl-1.1",
    "commons-clause",
}

FORBIDDEN_CLASSIFIER_FRAGMENTS = (
    "agpl",
    "sspl",
    "gnu general public license v3",
    "gnu affero",
)


def _tokens(expr: str) -> list[str]:
    return [t for t in re.split(r"[^\w.+-]+", expr.lower()) if t]


def spdx_forbidden(expr: str) -> str | None:
    """Return hit if a short licence expression names a forbidden SPDX id."""
    if not expr or "\n" in expr or len(expr) > 120:
        # Long prose → ignore here; classifiers handle real copyleft declarations.
        return None
    low = expr.lower().strip()
    if "lgpl" in low:
        return None
    for tok in _tokens(low):
        if tok in FORBIDDEN_SPDX:
            return tok
    if "agpl" in low:
        return "agpl"
    if re.search(r"\bgpl[-_]?3\b", low) and "lgpl" not in low:
        return "gpl-3"
    return None


def classifier_forbidden(classifiers: list[str]) -> str | None:
    for c in classifiers:
        low = c.lower()
        if "license ::" not in low:
            continue
        if "lesser general public" in low or "lgpl" in low:
            continue
        for frag in FORBIDDEN_CLASSIFIER_FRAGMENTS:
            if frag in low:
                return frag
        if "gnu general public license" in low and "v3" in low:
            return "gpl-3-classifier"
    return None


def scan_python() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    from importlib import metadata

    findings: list[dict[str, str]] = []
    lgpl_notes: list[dict[str, str]] = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or getattr(dist, "name", "unknown")
        lic = (
            dist.metadata.get("License-Expression")
            or dist.metadata.get("License")
            or ""
        )
        classifiers = list(dist.metadata.get_all("Classifier") or [])
        hit = spdx_forbidden(lic) or classifier_forbidden(classifiers)
        if hit:
            findings.append(
                {
                    "ecosystem": "pip",
                    "name": str(name),
                    "license": lic.split("\n")[0][:160],
                    "hit": hit,
                }
            )
        blob = (lic + " " + " ".join(classifiers)).lower()
        if "lgpl" in blob or "lesser general public" in blob:
            lgpl_notes.append(
                {
                    "ecosystem": "pip",
                    "name": str(name),
                    "license": lic.split("\n")[0][:160],
                }
            )
    return findings, lgpl_notes


def scan_npm() -> list[dict[str, str]]:
    lock = ROOT / "package-lock.json"
    if not lock.exists():
        return []
    data = json.loads(lock.read_text(encoding="utf-8"))
    findings: list[dict[str, str]] = []
    for path, meta in (data.get("packages") or {}).items():
        if not path:
            continue
        lic = meta.get("license") or ""
        if isinstance(lic, dict):
            lic = lic.get("type") or ""
        hit = spdx_forbidden(str(lic))
        if hit:
            findings.append(
                {"ecosystem": "npm", "name": path, "license": str(lic), "hit": hit}
            )
    return findings


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed-fail", action="store_true")
    args = p.parse_args()
    if args.seed_fail:
        print("Seeded failure: synthetic GPL-3.0 dependency 'evil-pkg'")
        print("❌ licence gate failed (seed)")
        return 1

    py_findings, lgpl_notes = scan_python()
    findings = py_findings + scan_npm()
    payload = {
        "ok": len(findings) == 0,
        "forbidden_findings": findings,
        "lgpl_review_notes": lgpl_notes,
        "policy": (
            "Fail on SPDX/classifier AGPL, GPL-3, SSPL, BUSL, Commons-Clause. "
            "LGPL noted but not failed. Long licence prose is not substring-scanned."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": payload["ok"],
                "forbidden": len(findings),
                "lgpl_notes": len(lgpl_notes),
                "report": str(OUT),
            },
            indent=2,
        )
    )
    if findings:
        for f in findings:
            print(f"❌ {f['ecosystem']}:{f['name']} licence={f['license']!r} hit={f['hit']}")
        return 1
    print("✅ licence allowlist gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
