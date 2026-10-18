# ADR 0018: Software Supply Chain Provenance, Dependency Pinning, and CycloneDX SBOM Generation

## Status
Accepted

## Context
As a clinical decision-support platform (SaMD / ISO 14971 / IEC 62304 / FDA 21 CFR Part 820), Vigil must guarantee the integrity, traceability, and security of all runtime and build-time software components. Modern medical device software faces critical supply-chain risks, including:
1. **Transitive Dependency Tampering & Malicious Injections:** Compromised upstream packages or typosquatting attacks that introduce unauthorized telemetry, backdoors, or unvetted algorithmic modifications.
2. **Build Non-Reproducibility:** Floating or unpinned version ranges (`^`, `~`, `>=`) that cause non-deterministic binary outputs across different CI runs or deployment environments.
3. **Regulatory Non-Compliance:** Failure to comply with US Executive Order 14028, NTIA Minimum Elements for SBOMs, and FDA guidance on *Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions* (Sept 2023).

## Decision

### 1. Zero Floating Versions and Lockfile Determinism
All software dependencies across all monorepo tiers must be strictly pinned to immutable cryptographic lockfiles:
* **Python Tier (`vigil-core`, `vigil-ml`, `vigil-api`, `vigil-eval`):** Governed by `uv.lock`. Direct dependencies in `pyproject.toml` are pinned with exact versions; resolution hashes are verified on every installation (`uv sync --frozen`).
* **Web Tier (`apps/web`):** Governed by `package-lock.json` with npm `lockfileVersion: 3`. Installations in CI must execute `npm ci` exclusively.
* **CI Actions:** All third-party GitHub Actions must be pinned to full 40-character commit SHAs (e.g. `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`).

### 2. Automated Multi-Ecosystem CycloneDX v1.5 SBOM Generation
Vigil implements an automated, self-contained SBOM generation engine (`scripts/generate_sbom.py`) adhering to the CycloneDX v1.5 JSON standard:
* **Python SBOM:** Ingests `uv.lock`, enumerating all direct and transitive wheel packages with Package URLs (`pkg:pypi/{name}@{version}`), scopes, and SHA-256 distribution hashes (`reports/sbom/sbom-python.cdx.json`).
* **NPM SBOM:** Ingests `package-lock.json`, extracting all runtime and development Node packages with Package URLs (`pkg:npm/{name}@{version}`) and integrity checksums (`reports/sbom/sbom-npm.cdx.json`).
* **CI Integration:** SBOM generation is executed as part of release staging and governance audits.

### 3. Vulnerability Disclosure & Remediation Policy
Vigil establishes a binding Vulnerability Policy (`docs/security/VULNERABILITY_POLICY.md`) aligned with ISO/IEC 29147 and ISO/IEC 30111:
* **Critical (CVSS 9.0–10.0):** Mandatory remediation and regression verification within **48 hours**.
* **High (CVSS 7.0–8.9):** Mandatory remediation within **7 days**.
* **Medium (CVSS 4.0–6.9):** Remediation within **30 days**.
* **Unmitigated High/Critical in Production Runtime:** Hard failure blocking merge to `main`.

## Consequences
- Every release candidate includes verifiable, machine-readable inventory artifacts for regulatory submission.
- Builds are 100% reproducible across local developer machines, GitHub Actions runners, and on-premise hospital installations.
- Vulnerability triage is governed by explicit clinical safety and data integrity SLAs.

## Amendment 1 (final-build Tier 0; corrections after VERDICT-P8B)

The original text over-described what was enforced. Corrections, each checkable:

1. **No artifact is signed.** The release manifest is a SHA-256 *hash manifest* (`"kind": "sha256-hash-manifest"`, `"signature": {"status": "unsigned"}`). Tooling to sign (cosign, key-based) and to verify exists in `scripts/generate_release_manifest.py` and is tested; producing the signing key is an owner action ([`docs/release/SIGNING.md`](../release/SIGNING.md)).
2. **"Direct dependencies pinned with exact versions" was not true.** Direct dependencies in `pyproject.toml` use lower bounds (`>=`); reproducibility comes from the committed lockfiles (`uv.lock`, `package-lock.json`) and frozen installs, not from exact specifiers.
3. **"100% reproducible builds" was never measured.** Bit-for-bit reproducibility is not claimed. What exists: a lockfile-determined dependency set and a CI job that regenerates the cheap study results and diffs them.
4. **The vulnerability gate was not enforced for the web tier.** `pip-audit` is now a blocking CI job (`dependency-audit`). `npm audit` found critical/high advisories in the locked `next@14.2.35` and `postcss`; remediation is tracked in the Tier-0 handover notes and the dependency-upgrade PR. Until it lands, the policy statement "unmitigated High/Critical in production runtime blocks merge" is **not met** for the web tier.
5. CI no longer installs `uv` with `curl | sh`; it uses `astral-sh/setup-uv` pinned by commit SHA and a pinned uv version.
