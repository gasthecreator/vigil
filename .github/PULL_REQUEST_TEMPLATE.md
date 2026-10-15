## What
<!-- One-paragraph summary of the change. -->

## Why
<!-- The clinical or engineering requirement. Link issue / ADR / proposal. -->
Closes #

## How
<!-- Approach, alternatives rejected, known trade-offs. -->

## Testing
<!-- Real command output and evidence. Never fake or mock verification. -->
- [ ] Unit tests added/updated (`pytest`, `vitest`)
- [ ] Property-based tests where applicable (Hypothesis)
- [ ] Leakage tests verified (if touching feature generation, splits, or models)
- [ ] `make test` passes cleanly

## Safety & Governance
- [ ] Adheres to `docs/DISCLAIMER.md` and `docs/MASTER_PLAN.md` §11.1
- [ ] `python3 scripts/check_claims.py` passes (no forbidden phrases, no unlabelled synthetic claims)
- [ ] No hardcoded machine paths (`/Users/...`, `/opt/homebrew/...`)
- [ ] No `.pkl` files in runtime paths
- [ ] All synthetic entities, endpoints, and UI views carry explicit `synthetic=True` indicators

## Checklist
- [ ] Conventional Commit format
- [ ] Documentation updated (Diataxis in `docs/`)
- [ ] CHANGELOG.md updated
- [ ] No secrets or untracked state committed
