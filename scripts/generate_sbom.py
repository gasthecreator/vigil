#!/usr/bin/env python3
"""scripts/generate_sbom.py

Automated Software Bill of Materials (SBOM) Generator.
Complies with CycloneDX v1.5 JSON specification and Executive Order 14028.
Master Plan §3, §11, Phase 8a Governance.

Generates:
- reports/sbom/sbom-python.cdx.json (from uv.lock)
- reports/sbom/sbom-npm.cdx.json (from package-lock.json)
"""

from __future__ import annotations

import hashlib
import json
import tomllib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent


def _deterministic_meta(components: List[Dict[str, Any]], lock_path: Path) -> Dict[str, str]:
    """Stable serial + timestamp so regenerate-and-diff is bit-identical across runs."""
    digest = hashlib.sha256(
        json.dumps(components, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    serial = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'vigil-sbom:{digest}')}"
    # Lockfile mtime (UTC) — changes only when dependencies change.
    ts = datetime.fromtimestamp(lock_path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {"serialNumber": serial, "timestamp": ts}


def generate_python_sbom() -> Dict[str, Any]:
    uv_lock = ROOT / "uv.lock"
    if not uv_lock.exists():
        raise FileNotFoundError(f"uv.lock not found at {uv_lock}")

    with open(uv_lock, "rb") as f:
        data = tomllib.load(f)

    packages = data.get("package", [])
    components: List[Dict[str, Any]] = []

    for pkg in packages:
        name = pkg.get("name")
        version = pkg.get("version")
        if not name or not version:
            continue

        comp = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name}@{version}",
            "scope": "required",
        }

        # Extract hash if present
        sdist = pkg.get("sdist")
        if isinstance(sdist, dict) and "hash" in sdist:
            h_str = sdist["hash"]
            if ":" in h_str:
                alg, h_val = h_str.split(":", 1)
                comp["hashes"] = [{"alg": alg.upper(), "content": h_val}]

        components.append(comp)

    components.sort(key=lambda c: c["name"])
    meta = _deterministic_meta(components, uv_lock)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": meta["serialNumber"],
        "version": 1,
        "metadata": {
            "timestamp": meta["timestamp"],
            "tools": [{"vendor": "Vigil Security", "name": "generate_sbom.py", "version": "1.0.0"}],
            "component": {
                "type": "application",
                "name": "vigil-python-workspace",
                "version": "0.1.0",
                "description": "Vigil Precision Oncology Python Core, ML & API Workspace",
            },
        },
        "components": components,
    }


def generate_npm_sbom() -> Dict[str, Any]:
    lock_path = ROOT / "package-lock.json"
    if not lock_path.exists():
        raise FileNotFoundError(f"package-lock.json not found at {lock_path}")

    with open(lock_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    components: List[Dict[str, Any]] = []
    seen: set[str] = set()

    packages = data.get("packages", {})
    for path, info in packages.items():
        if not path:
            continue
        name = info.get("name") or (path.split("node_modules/")[-1] if "node_modules/" in path else path)
        version = info.get("version")
        if not name or not version:
            continue

        key = f"{name}@{version}"
        if key in seen:
            continue
        seen.add(key)

        comp = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:npm/{name}@{version}",
            "scope": "required",
        }

        integrity = info.get("integrity")
        if integrity and "-" in integrity:
            alg, h_val = integrity.split("-", 1)
            comp["hashes"] = [{"alg": alg.upper(), "content": h_val}]

        components.append(comp)

    components.sort(key=lambda c: c["name"])
    meta = _deterministic_meta(components, lock_path)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": meta["serialNumber"],
        "version": 1,
        "metadata": {
            "timestamp": meta["timestamp"],
            "tools": [{"vendor": "Vigil Security", "name": "generate_sbom.py", "version": "1.0.0"}],
            "component": {
                "type": "application",
                "name": "vigil-web-frontend",
                "version": "0.1.0",
                "description": "Vigil Precision Oncology Next.js & UI Components",
            },
        },
        "components": components,
    }


def main() -> None:
    out_dir = ROOT / "reports" / "sbom"
    out_dir.mkdir(parents=True, exist_ok=True)

    py_sbom = generate_python_sbom()
    py_path = out_dir / "sbom-python.cdx.json"
    with open(py_path, "w", encoding="utf-8") as f:
        json.dump(py_sbom, f, indent=2)
    print(f"✅ Python CycloneDX SBOM written to {py_path} ({len(py_sbom['components'])} components)")

    npm_sbom = generate_npm_sbom()
    npm_path = out_dir / "sbom-npm.cdx.json"
    with open(npm_path, "w", encoding="utf-8") as f:
        json.dump(npm_sbom, f, indent=2)
    print(f"✅ NPM CycloneDX SBOM written to {npm_path} ({len(npm_sbom['components'])} components)")


if __name__ == "__main__":
    main()
