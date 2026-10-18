# Signing a Vigil release manifest (owner procedure)

**Status today: nothing in this repository is signed.** `docs/release/RELEASE_MANIFEST_<release>.json` is a SHA-256 *hash manifest*. It lets a reader detect that a listed file differs from what was recorded at `git_commit`; it does **not** prove who produced the manifest, because anyone who can edit the repository can regenerate it. The manifest therefore carries `"signature": {"status": "unsigned"}` and `"kind": "sha256-hash-manifest"`.

The tooling to sign and verify exists and is tested (`scripts/generate_release_manifest.py`, `tests/governance/test_release_manifest.py`, which round-trips a signature with an *ephemeral test key* and checks that a tampered manifest fails). The key is an owner action because only the owner can hold a signing identity (`docs/HANDOVER.md`, item H-SIGN-1).

## One-time: create the key (owner, offline machine preferred)

```bash
brew install cosign            # or see https://docs.sigstore.dev/cosign/installation/
cosign generate-key-pair       # writes cosign.key (private, password-protected) and cosign.pub
```

- Keep `cosign.key` offline; never commit it (`.gitignore` blocks `*.key`).
- Commit `cosign.pub` as `docs/release/cosign.pub` in a PR the owner authors, and publish its fingerprint (`sha256sum docs/release/cosign.pub`) somewhere an attacker with repository access cannot also edit (for example the owner's website or a signed email).

## Per release

```bash
python scripts/generate_release_manifest.py generate --release v1.0.0-rc.2   # refuses a dirty tree
python scripts/generate_release_manifest.py verify   --release v1.0.0-rc.2
python scripts/generate_release_manifest.py sign     --release v1.0.0-rc.2 --key /secure/path/cosign.key
git add docs/release/RELEASE_MANIFEST_v1.0.0-rc.2.json docs/release/RELEASE_MANIFEST_v1.0.0-rc.2.json.cosign.bundle
```

After signing, update the manifest's `signature` block only by re-running `generate` and `sign` (editing the JSON invalidates the signature).

## Verification by anyone

```bash
python scripts/generate_release_manifest.py verify-signature --release v1.0.0-rc.2 --pubkey docs/release/cosign.pub
python scripts/generate_release_manifest.py verify           --release v1.0.0-rc.2
```

The first command checks the signature over the manifest; the second re-hashes the files. Both must pass, and the public key fingerprint must match the one published out of band.

## Limits (stated so nobody over-reads a green check)

- Key-based signing here does not use a transparency log (so it works air-gapped). Revocation is by publishing a new key.
- A signature authenticates the manifest, not the correctness of the software. Nothing here is a regulatory submission or a clearance.
- Keyless signing (GitHub OIDC + Rekor) is a possible CI path once the owner decides on it; it is not configured.
