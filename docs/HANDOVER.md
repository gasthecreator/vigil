# Vigil — Handover: what only a human can do

> Everything that can be built, verified and honestly described without outside people, data or approvals is in the repository. This file lists what remains and exactly how to do it. Status words: **READY** (artifact drafted, only the human step remains), **BLOCKED** (needs something outside the repository first). Items are appended by tier; Tier 3 turns this into the final hand-over. Maturity stays **L0** until real-data validation exists (overseer-owned).

## A. Repository / release actions (owner)

| ID | Action | Why only a human | Exact steps | Status |
|---|---|---|---|---|
| H-GH-1 | Protect `main` | GitHub settings are owner-only; the agent must not change them | Run section 1 of [`docs/ops/GITHUB-SETTINGS.md`](ops/GITHUB-SETTINGS.md) (required-check names there were corrected in Tier 0 to the real job names). Verify: `python scripts/audit_repo_standards.py --online` → item T1.6 ≥ 2 | READY. Observed 2026-10-18: no protection and no ruleset on `main` |
| H-GH-2 | Enable secret scanning + push protection | Same | Section 2 of the same file; verify T3.1 online | READY |
| H-GH-3 | Second maintainer / reviewer | A person | Add them to `.github/CODEOWNERS`; then set `required_approving_review_count` to 1 and `require_code_owner_review` to true (note 2 in GITHUB-SETTINGS) | BLOCKED on a person |
| H-SIGN-1 | Create the release-signing key and sign `v1.0.0-rc.*` | Only the owner may hold a signing identity | [`docs/release/SIGNING.md`](release/SIGNING.md): `cosign generate-key-pair`, commit `cosign.pub`, publish the fingerprint out-of-band, run `generate_release_manifest.py sign` | READY (tooling tested; nothing in the repository is signed today) |
| H-OSSF-1 | Register for the OpenSSF Best Practices badge | Needs a maintainer account | <https://www.bestpractices.dev>; record the project id in `README.md` | READY |

## B. Clinical, legal and data actions (see `docs/MASTER_PLAN.md` §17.3)

| ID | Action | Where the prepared material is |
|---|---|---|
| H-001 | Institutional ethics (IRB/REC) submission for any study with patients | `docs/clinical/PARTNERSHIP/ETHICS-APPLICATION.md` (draft, unsigned) |
| H-002 | Data-use agreements for real datasets (SEER, METABRIC/TCGA access terms) | `docs/data/ACCESS.md`, `data/dataset_cards/` |
| H-003 | Regulator pre-submission meeting (NAFDAC / SaMD) | `docs/regulatory/` — all documents are `DRAFT-UNREVIEWED` |
| H-004 | Production key management (cloud KMS / HSM) and field-encryption master key provisioning | `docs/runbooks/`, `.env.example` |
| H-005 | Recruit participants for IEC 62366-1 summative usability testing | `docs/usability/USABILITY_TEST_PROTOCOL.md` |

## C. Known unmet items that are not human actions (tracked so they are not forgotten)

| ID | Item | Evidence | Plan |
|---|---|---|---|
| X-DEP-1 | (RESOLVED on branch `fix/web-next15-security`, pending merge) `npm audit --omit=dev` reported 1 critical and 1 high advisory for `next@14.2.35` and `postcss`. Upgraded to `next@15.5.28` with a `postcss` override; `npm audit --package-lock-only --omit=dev` now reports 0 vulnerabilities and is a CI gate. Dev-only tooling advisories remain (`braces`/`tailwindcss`/`eslint-config-next` chain, 7 high, 2 moderate; build-time only, fix needs `tailwindcss@4`, a breaking change) | `cd apps/web && npm audit` | Merge that PR after the owner reviews; the dev-tooling advisories stay OPEN |
| X-AUD-1 | Repo-standards audit is below its Master-Plan target in every tier | `docs/audits/REPO-AUDIT-P15.md` (script-written; gap list at the end) | Items that need the owner are in section A; the rest are listed there with fixes |
| X-ADR-0018-2 | Direct dependencies use lower bounds (`>=`), reproducibility rests on lockfiles | ADR-0018 Amendment 1 | Documented, not changed |
