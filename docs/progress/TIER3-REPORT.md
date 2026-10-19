# Tier 3 report: finish, verify, hand over

> Status: SUBMITTED FOR REVIEW. Verdict, maturity and every overseer column are untouched. Maturity stays L0. Release candidate `v1.0.0-rc.2` is prepared in-repo, **not published**.

## Outcome in one paragraph
Tier 3 closes the final-build documentation and release-candidate loop without claiming clinical readiness: `docs/STATUS.md` is script-generated from the ledger, OPEN hazards, stubs and CI job names; `make demo` seeds synthetic patients and starts API + web with an owner walkthrough script; `docs/clinical/PARTNERSHIP/PARTNER-PACKET.md` states claim boundaries for hospital outreach; `docs/HANDOVER.md` section D lists who must sign what before any patient is touched; an honesty sweep corrected unsupported README/plan badge, walkthrough and value-proposition wording; SBOMs and `RELEASE_MANIFEST_v1.0.0-rc.2.json` refresh the candidate; CI gains STATUS freshness and a clean-clone study reproducibility job.

## What was built
| Item | Where |
|---|---|
| STATUS generator + freshness gate | `scripts/generate_status.py`, `docs/STATUS.md`, CI step |
| Synthetic demo | `make demo`, `scripts/run_demo.py`, `docs/demo/OWNER-SCRIPT.md` |
| Partner packet | `docs/clinical/PARTNERSHIP/PARTNER-PACKET.md` (+ honesty edits to VALUE-PROPOSITION) |
| Handover section D | `docs/HANDOVER.md` (H-201…H-213) |
| Honesty sweep | README plan badge v1.3; COGNITIVE_WALKTHROUGHS 2.2; VALUE-PROPOSITION |
| rc.2 | CHANGELOG, SBOMs, `scripts/generate_release_manifest.py` default, manifest, REPRODUCIBILITY |
| Clean-clone CI | `clean-clone-reproducibility` job in `.github/workflows/ci.yml` |

## Findings and deviations
1. Manifest signing remains owner-only (H-SIGN-1); rc.2 hash manifest is **unsigned**.
2. Full local regression of every acceptance suite is expected green via the same CI jobs as main; this report does not invent pytest transcripts.
3. `git clone --no-local` clean-clone job re-runs `verify_study_reproducibility.py` only (cheap/deterministic studies), matching the existing verifier scope — not a full re-train of K4/K6.

## Files changed outside this item's scope
None intentional beyond shared Makefile/CI/docs index and e2e seed path parameterisation used by the demo.

## `tests/acceptance_*`
Untouched.
