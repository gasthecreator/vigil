#!/usr/bin/env python3
"""Third-party licence inventory + NOTICE (G-10), runtime dependencies only.

Sources: the locked runtime closure (`uv export --no-dev`, package-lock.json production entries) for the
package list, installed distribution metadata for the licence text. Licence names are normalised to short SPDX-style
identifiers; anything that cannot be resolved is listed as `needs_review` (never silently "UNKNOWN").
Output is deterministic (no timestamps) so CI can diff the committed files.

The same policy as scripts/check_licences.py applies: a runtime package with a forbidden licence
(AGPL / GPL-3 / SSPL / BUSL / Commons Clause) fails the run. `--seed-fail` pushes a synthetic AGPL package
through that real policy path and must exit non-zero.

  uv run python scripts/generate_licence_inventory.py          # write reports/quality/LICENCE_INVENTORY.json + NOTICE
  uv run python scripts/generate_licence_inventory.py --check  # fail if committed files are stale
  uv run python scripts/generate_licence_inventory.py --seed-fail
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from check_licences import classifier_forbidden, spdx_forbidden  # noqa: E402

OUT_JSON = ROOT / "reports" / "quality" / "LICENCE_INVENTORY.json"
NOTICE = ROOT / "NOTICE"

# Classifier trove name -> SPDX-ish id
CLASSIFIER_MAP = {
    "apache software license": "Apache-2.0",
    "mit license": "MIT",
    "bsd license": "BSD",
    "isc license (iscl)": "ISC",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "python software foundation license": "PSF-2.0",
    "gnu lesser general public license v3 (lgplv3)": "LGPL-3.0",
    "gnu lesser general public license v2 or later (lgplv2+)": "LGPL-2.1-or-later",
    "the unlicense (unlicense)": "Unlicense",
    "public domain": "Public-Domain",
}
# Packages whose metadata carries no usable licence field; verified against upstream by hand.
OVERRIDES = {
    "colorama": "BSD-3-Clause",
    "cycler": "BSD-3-Clause",
    "tomli": "MIT",
    "tzdata": "Apache-2.0",
    "triton": "MIT",
}
# Linux-only CUDA wheels pulled in by torch: proprietary NVIDIA redistributables, not OSI licences. They are listed
# so NOTICE is honest; confirm the NVIDIA EULA before shipping images that bundle them.
NVIDIA_PREFIXES = ("nvidia-", "cuda-")
NVIDIA_LICENCE = "LicenseRef-NVIDIA-Proprietary"
LONG_TEXT_HINTS = (
    ("apache license", "Apache-2.0"),
    ("permission is hereby granted, free of charge", "MIT"),
    ("redistribution and use in source and binary forms", "BSD"),
    ("mozilla public license", "MPL-2.0"),
)


def normalise(
    name: str, license_expr: str, license_field: str, classifiers: list[str]
) -> str | None:
    if name.lower() in OVERRIDES:
        return OVERRIDES[name.lower()]
    if name.lower().startswith(NVIDIA_PREFIXES):
        return NVIDIA_LICENCE
    if license_expr.strip():
        return license_expr.strip()
    lic = license_field.strip()
    if lic and "\n" not in lic and len(lic) <= 80 and lic.upper() != "UNKNOWN":
        return lic
    found = []
    for c in classifiers:
        parts = [p.strip() for p in c.split("::")]
        if parts[0].lower() == "license" and len(parts) >= 3:
            found.append(CLASSIFIER_MAP.get(parts[-1].lower(), parts[-1]))
    if found:
        return " OR ".join(sorted(set(found)))
    low = lic.lower()
    for hint, spdx in LONG_TEXT_HINTS:
        if hint in low:
            return spdx
    return None


def python_runtime_pins() -> dict[str, str]:
    """name -> locked version for the whole runtime closure, including platform-marker-only packages."""
    out = subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--all-packages",
            "--no-dev",
            "--no-hashes",
            "--no-emit-workspace",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {
        m.group(1).lower().replace("_", "-"): m.group(2)
        for m in re.finditer(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)", out, re.M)
    }


def python_entries(pins: dict[str, str] | None = None) -> list[dict]:
    """One row per locked runtime package (deterministic across platforms / installed groups).

    Licence text comes from installed metadata when present; a package that is locked but not installed here
    (platform-marker-only, e.g. colorama on Windows) is resolved from OVERRIDES or flagged `needs_review`."""
    pins = python_runtime_pins() if pins is None else pins
    installed = {}
    for dist in metadata.distributions():
        nm = (dist.metadata["Name"] or "").lower().replace("_", "-")
        installed.setdefault(nm, dist)
    rows = []
    for nm, version in sorted(pins.items()):
        dist = installed.get(nm)
        if dist is not None:
            name = dist.metadata["Name"]
            classifiers = list(dist.metadata.get_all("Classifier") or [])
            lic = normalise(
                name,
                dist.metadata.get("License-Expression") or "",
                dist.metadata.get("License") or "",
                classifiers,
            )
            version = dist.version
        else:
            name, classifiers, lic = nm, [], normalise(nm, "", "", [])
        rows.append(
            {
                "ecosystem": "pip",
                "name": name,
                "version": version,
                "license": lic or "needs_review",
                "needs_review": lic is None,
                "_classifiers": classifiers,
            }
        )
    return sorted(rows, key=lambda r: r["name"].lower())


def npm_entries() -> list[dict]:
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    rows = {}
    for path, pkg in lock.get("packages", {}).items():
        if not path or pkg.get("dev") or "node_modules/" not in path:
            continue
        name = path.rsplit("node_modules/", 1)[1]
        if name.startswith("@vigil/") or pkg.get("link"):
            continue  # our own workspace packages
        lic = pkg.get("license")
        if isinstance(lic, dict):
            lic = lic.get("type")
        rows[(name, pkg.get("version", ""))] = lic
    return [
        {
            "ecosystem": "npm",
            "name": n,
            "version": v,
            "license": lic or "needs_review",
            "needs_review": not lic,
            "_classifiers": [],
        }
        for (n, v), lic in sorted(rows.items())
    ]


def policy_violations(entries: list[dict]) -> list[str]:
    bad = []
    for e in entries:
        hit = spdx_forbidden(e["license"]) or classifier_forbidden(e.get("_classifiers", []))
        if hit:
            bad.append(
                f"{e['ecosystem']}:{e['name']} {e['version']} licence={e['license']} ({hit})"
            )
    return bad


def render(entries: list[dict]) -> tuple[str, str]:
    public = [{k: v for k, v in e.items() if not k.startswith("_")} for e in entries]
    unresolved = [e["name"] for e in public if e["needs_review"]]
    payload = {
        "scope": "runtime dependencies only (uv export --no-dev; package-lock production entries)",
        "count": len(public),
        "needs_review_count": len(unresolved),
        "needs_review": unresolved,
        "packages": public,
    }
    lines = [
        "Vigil",
        "Copyright (c) Vigil contributors",
        "",
        "Vigil is licensed under the Apache License 2.0 (see LICENSE).",
        "",
        "Third-party runtime components (full inventory: reports/quality/LICENCE_INVENTORY.json):",
        "",
    ]
    for e in public:
        flag = "  [licence needs review]" if e["needs_review"] else ""
        lines.append(f"  - {e['name']} {e['version']} ({e['ecosystem']}): {e['license']}{flag}")
    if any(e["license"] == NVIDIA_LICENCE for e in public):
        lines += [
            "",
            "Note: the NVIDIA/CUDA packages above are proprietary redistributables installed on Linux (pulled in by",
            "torch). They are not open-source licences; review the NVIDIA EULA before distributing images that bundle them.",
        ]
    lines += ["", "Regenerate: uv run python scripts/generate_licence_inventory.py", ""]
    return json.dumps(payload, indent=2, sort_keys=True) + "\n", "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--check", action="store_true", help="fail if committed NOTICE / inventory are stale"
    )
    ap.add_argument(
        "--seed-fail", action="store_true", help="add a synthetic AGPL package; must exit non-zero"
    )
    args = ap.parse_args()

    entries = python_entries() + npm_entries()
    if args.seed_fail:
        entries.append(
            {
                "ecosystem": "pip",
                "name": "seeded-agpl-package",
                "version": "0.0.0",
                "license": "AGPL-3.0-only",
                "needs_review": False,
                "_classifiers": [],
            }
        )
    bad = policy_violations(entries)
    if bad:
        print("❌ forbidden licences in runtime dependencies:", *bad, sep="\n  ", file=sys.stderr)
        return 1

    inv, notice = render(entries)
    if args.check:
        stale = [
            p.name
            for p, new in ((OUT_JSON, inv), (NOTICE, notice))
            if not p.exists() or p.read_text(encoding="utf-8") != new
        ]
        if stale:
            print(f"❌ stale (regenerate with the script): {stale}", file=sys.stderr)
            return 1
        print("✅ NOTICE and licence inventory are fresh")
        return 0
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(inv, encoding="utf-8")
    NOTICE.write_text(notice, encoding="utf-8")
    n_review = json.loads(inv)["needs_review_count"]
    print(
        f"Wrote {OUT_JSON.name} and NOTICE ({len(entries)} runtime packages, {n_review} need review)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
