#!/usr/bin/env python3
"""scripts/generate_release_manifest.py

SHA-256 *hash manifest* for a Vigil release candidate, plus tooling to sign and verify it.

What this is, precisely
  * ``generate``  writes docs/release/RELEASE_MANIFEST_<release>.json: path, size and SHA-256 of every
    listed artifact as committed at HEAD (``git show HEAD:path``), refusing if a listed file has
    uncommitted changes (a manifest of a dirty tree would not describe any commit).
  * ``verify``    re-hashes the files and fails on any missing file or digest mismatch.
  * ``sign``      signs the manifest file with cosign (key-based) and writes <manifest>.cosign.bundle.
                  The private key belongs to the owner and is never in this repository.
  * ``verify-signature``  checks <manifest>.cosign.bundle against a public key.

A hash manifest alone is NOT a signature: anyone who can edit the repository can regenerate it.
The manifest says ``"signature": {"status": "unsigned"}`` until ``sign`` has been run by the key owner.
See docs/release/SIGNING.md for the owner procedure.

Usage
  python scripts/generate_release_manifest.py generate [--release v1.0.0-rc.1]
  python scripts/generate_release_manifest.py verify   [--release v1.0.0-rc.1]
  python scripts/generate_release_manifest.py sign --key cosign.key [--release ...]
  python scripts/generate_release_manifest.py verify-signature --pubkey cosign.pub [--release ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RELEASE = "v1.0.0-rc.2"

ARTIFACTS_TO_MANIFEST = [
    # Safety and Security
    "docs/safety/HAZARD_LOG.md",
    "docs/security/THREAT_MODEL.md",
    "docs/security/VULNERABILITY_POLICY.md",
    # Regulatory (all DRAFT-UNREVIEWED)
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def manifest_path(release: str, root: Path = REPO_ROOT) -> Path:
    return root / "docs" / "release" / f"RELEASE_MANIFEST_{release}.json"


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def generate_manifest(
    release: str,
    artifacts: list[str] | None = None,
    root: Path = REPO_ROOT,
    allow_dirty: bool = False,
    from_workdir: bool = False,
) -> dict:
    artifacts = artifacts if artifacts is not None else ARTIFACTS_TO_MANIFEST
    head = _git(root, "rev-parse", "HEAD").strip()
    dirty = set(_git(root, "status", "--porcelain", "--", *artifacts).split("\n")) - {""}
    if dirty and not allow_dirty and not from_workdir:
        raise SystemExit("refusing: listed artifacts have uncommitted changes:\n  " + "\n  ".join(sorted(dirty)))
    entries, missing = [], []
    for rel in artifacts:
        if from_workdir:
            path = root / rel
            if not path.is_file():
                missing.append(rel)
                continue
            data = path.read_bytes()
            entries.append({"path": rel, "sha256": sha256_bytes(data), "size_bytes": len(data)})
        else:
            r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=root, capture_output=True)
            if r.returncode != 0:
                missing.append(rel)
                continue
            entries.append({"path": rel, "sha256": sha256_bytes(r.stdout), "size_bytes": len(r.stdout)})
    if missing:
        raise SystemExit(f"refusing: listed artifacts not committed at HEAD: {missing}")
    source = "working tree at generate time" if from_workdir else "as committed at git_commit"
    return {
        "release": release,
        "kind": "sha256-hash-manifest",
        "description": f"Vigil release candidate {release}: SHA-256 digests of the listed artifacts ({source})",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": head,
        "artifact_count": len(entries),
        "artifacts": entries,
        "signature": {
            "status": "unsigned",
            "note": "A hash manifest is not a signature. Signing requires the owner's key (docs/release/SIGNING.md).",
        },
    }


def verify_manifest(manifest: dict, root: Path = REPO_ROOT) -> list[str]:
    problems = []
    for a in manifest["artifacts"]:
        p = root / a["path"]
        if not p.is_file():
            problems.append(f"MISSING {a['path']}")
        elif sha256_file(p) != a["sha256"]:
            problems.append(f"MISMATCH {a['path']}")
    if manifest.get("artifact_count") != len(manifest["artifacts"]):
        problems.append("artifact_count does not match artifacts list")
    return problems


def _cosign() -> str:
    exe = shutil.which("cosign")
    if not exe:
        raise SystemExit("cosign not found. Install it (https://docs.sigstore.dev/cosign/installation/) - see docs/release/SIGNING.md")
    return exe


def bundle_path(manifest_file: Path) -> Path:
    return manifest_file.with_suffix(manifest_file.suffix + ".cosign.bundle")


def sign(manifest_file: Path, key: Path) -> Path:
    """Sign with a cosign private key (the owner is prompted for the key password on the terminal).

    No transparency-log upload is requested (offline/air-gapped friendly); the bundle contains the
    signature only. Keyless (OIDC + Rekor) signing is the CI path described in docs/release/SIGNING.md.
    """
    bundle = bundle_path(manifest_file)
    r = subprocess.run(
        [_cosign(), "sign-blob", "--yes", "--key", str(key), "--use-signing-config=false", "--tlog-upload=false",
         "--bundle", str(bundle), str(manifest_file)],
        stdout=subprocess.DEVNULL,  # stdin/stderr stay attached so the password prompt works
    )
    if r.returncode != 0:
        raise SystemExit("cosign sign-blob failed")
    return bundle


def verify_signature(manifest_file: Path, pubkey: Path) -> tuple[bool, str]:
    bundle = bundle_path(manifest_file)
    if not bundle.is_file():
        return False, f"no signature bundle {bundle.name}"
    r = subprocess.run(
        [_cosign(), "verify-blob", "--key", str(pubkey), "--bundle", str(bundle), "--insecure-ignore-tlog=true", str(manifest_file)],
        capture_output=True, text=True,
    )
    last = [ln for ln in (r.stderr + r.stdout).strip().splitlines() if ln and not ln.startswith("WARNING")]
    return r.returncode == 0, (last[-1] if last else "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["generate", "verify", "sign", "verify-signature"])
    ap.add_argument("--release", default=DEFAULT_RELEASE)
    ap.add_argument("--key", type=Path)
    ap.add_argument("--pubkey", type=Path)
    ap.add_argument(
        "--from-workdir",
        action="store_true",
        help="Hash working-tree files (tag release CI after regenerating SBOMs). Default hashes git HEAD blobs.",
    )
    a = ap.parse_args(argv)
    mp = manifest_path(a.release)
    if a.command == "generate":
        m = generate_manifest(a.release, from_workdir=a.from_workdir, allow_dirty=a.from_workdir)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        print(f"wrote hash manifest ({m['artifact_count']} artifacts, UNSIGNED) -> {mp.relative_to(REPO_ROOT)}")
        return 0
    if a.command == "verify":
        problems = verify_manifest(json.loads(mp.read_text()))
        for p in problems:
            print(p)
        print("manifest verified" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if a.command == "sign":
        if not a.key:
            raise SystemExit("--key required")
        print(f"wrote {sign(mp, a.key)}")
        return 0
    if not a.pubkey:
        raise SystemExit("--pubkey required")
    ok, msg = verify_signature(mp, a.pubkey)
    print(("signature valid: " if ok else "signature INVALID: ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
