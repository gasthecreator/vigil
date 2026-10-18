#!/usr/bin/env python3
"""
scripts/generate_release_manifest.py

Generates the release manifest with SHA-256 digests for Vigil Release Candidate v1.0.0-rc.1.
Covers clinical safety, regulatory files, threat models, SBOMs, study reports, and operational specs.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ARTIFACTS_TO_MANIFEST = [
    # Safety and Security
    "docs/safety/HAZARD_LOG.md",
    "docs/security/THREAT_MODEL.md",
    "docs/security/VULNERABILITY_POLICY.md",
    # Regulatory
    "docs/regulatory/INTENDED_USE.md",
    "docs/regulatory/DPIA.md",
    "docs/regulatory/PCCP.md",
    "docs/regulatory/CLINICAL_EVALUATION_PLAN.md",
    "docs/regulatory/RISK_MANAGEMENT_FILE.md",
    # Studies & Pre-registrations
    "docs/studies/PREREG-M7-TWIN.md",
    "docs/studies/PREREG-S8-K7.md",
    "docs/studies/PREREG-M10.md",
    # Usability & Human Factors
    "docs/usability/HEURISTIC_EVALUATION.md",
    "docs/usability/COGNITIVE_WALKTHROUGHS.md",
    "docs/usability/USABILITY_TEST_PROTOCOL.md",
    # Deployment & Resilience
    "docs/deployment/ON_PREM_INSTALL.md",
    "docs/resilience/DISASTER_RECOVERY.md",
    # SBOMs
    "reports/sbom/sbom-python.cdx.json",
    "reports/sbom/sbom-npm.cdx.json",
    # Performance & Soak Reports
    "reports/load/LOAD_TEST_RESULTS.json",
    "reports/load/SOAK_TEST_RESULTS.json",
    # ML & Simulation Study Reports
    "reports/ml/STUDY_S8_K7_CAUSAL.json",
    "reports/ml/STUDY_M10_MISSED_SIGNALS.json",
    "reports/ml/STUDY_M7_DIGITAL_TWIN.json",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_manifest() -> dict:
    entries = []
    for rel_path in ARTIFACTS_TO_MANIFEST:
        abs_path = REPO_ROOT / rel_path
        if not abs_path.exists():
            print(f"⚠️  Warning: {rel_path} does not exist yet. Skipping hash.")
            continue
        size = abs_path.stat().st_size
        digest = sha256_file(abs_path)
        entries.append({
            "path": rel_path,
            "sha256": digest,
            "size_bytes": size,
        })

    manifest = {
        "release": "v1.0.0-rc.1",
        "description": "Vigil Precision Oncology CDSS - Release Candidate 1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": os.popen("git rev-parse HEAD").read().strip(),
        "artifact_count": len(entries),
        "artifacts": entries,
    }
    return manifest


def main():
    manifest = generate_manifest()
    out_path = REPO_ROOT / "docs/release/RELEASE_MANIFEST_v1.0.0-rc.1.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"✅ Generated release manifest with {manifest['artifact_count']} artifacts: {out_path}")


if __name__ == "__main__":
    main()
