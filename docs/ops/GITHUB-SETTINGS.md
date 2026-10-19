# Vigil — GitHub Repository Security & Ruleset Configuration

> **Target Repository:** `gasthecreator/vigil`  
> **Status:** Pending Human Action (Product Owner with GitHub Admin Rights).  
> **Reference:** `docs/MASTER_PLAN.md` §12, §17.3 and `docs/PROGRESS.md` H-001.

This runbook contains the exact commands and settings to configure repository governance, branch protection, and OpenSSF Scorecard requirements.

---

## 1. Branch Protection & Ruleset for `main`

Run the following GitHub CLI commands to create a protective ruleset on the `main` branch requiring passing CI checks and linear history:

```bash
# Set repository context
REPO="gasthecreator/vigil"

# 1. Ensure default branch is main
gh repo edit "$REPO" --default-branch main

# 2. Configure ruleset for branch protection on main
gh api --method POST -H "Accept: application/vnd.github+json" \
  "/repos/$REPO/rulesets" \
  --input - << 'EOF'
{
  "name": "Production Quality & Security Gate",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "deletion"
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "required_linear_history"
    },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          {"context": "claims-and-governance"},
          {"context": "backend-lint-and-test"},
          {"context": "frontend-lint-and-build"},
          {"context": "e2e-and-lighthouse"},
          {"context": "dependency-audit"},
          {"context": "clean-clone-reproducibility"},
          {"context": "docker-build"},
          {"context": "postgres-api-suite"},
          {"context": "analyze (python)"},
          {"context": "analyze (javascript-typescript)"}
        ]
      }
    }
  ]
}
EOF
```

---

## 2. Security Feature Activation

Run the following commands to enable automated secret scanning and vulnerability alerts:

```bash
# Enable vulnerability alerts and automated security fixes
gh api --method PUT -H "Accept: application/vnd.github+json" \
  "/repos/$REPO/vulnerability-alerts"

gh api --method PUT -H "Accept: application/vnd.github+json" \
  "/repos/$REPO/automated-security-fixes"

# Enable secret scanning and push protection (if GitHub Advanced Security is available)
gh api --method PATCH -H "Accept: application/vnd.github+json" \
  "/repos/$REPO" \
  -f security_and_analysis[secret_scanning][status]=enabled \
  -f security_and_analysis[secret_scanning_push_protection][status]=enabled
```

---

## 3. Verification Checklist

- [ ] `main` branch cannot be force-pushed or deleted.
- [ ] Direct pushes to `main` are blocked; all changes must pass through pull requests.
- [ ] Required status checks include:
  - `claims-and-governance`, `backend-lint-and-test`, `frontend-lint-and-build`, `e2e-and-lighthouse`, `dependency-audit`, `clean-clone-reproducibility`, `docker-build`, `postgres-api-suite`, `analyze (python)`, `analyze (javascript-typescript)`
  - (names verified against `gh api repos/gasthecreator/vigil/commits/main/check-runs`; a required context that no job reports blocks every merge forever)
- [ ] Review requirement: see the note below.
- [ ] Secret scanning and Dependabot alerts are active.
- [ ] **Dependency graph** enabled (Settings → Code security → Dependency graph) so `actions/dependency-review-action` can run on PRs. Private repos also need GitHub Advanced Security. Until then the quality-gates job records PARTIAL in `reports/quality/DEPENDENCY_REVIEW.json` and does not block; `pip-audit` / `npm audit` remain hard gates.

```bash
# Enable dependency graph (public repos) — adjust for private + GHAS as needed:
gh api -X PUT "repos/gasthecreator/vigil/vulnerability-alerts"
# UI: https://github.com/gasthecreator/vigil/settings/security_analysis
```

## 4. Notes added in the final-build Tier 0

1. **Check names.** The first version of this file listed contexts (`lint-and-typecheck`, `unit-and-property-tests`, `claims-policy-check`) that no workflow job reports. Applied as written, it would have made `main` unmergeable. The contexts above are the real job names.
2. **Reviews with a single maintainer.** GitHub does not let a pull-request author approve their own PR, and `.github/CODEOWNERS` currently names one owner. Requiring one approval plus code-owner review would therefore lock the owner out. The ruleset above requires **0** approvals and no code-owner review so that the required status checks and PR-only flow are the gate. As soon as a second maintainer exists, raise `required_approving_review_count` to 1 and `require_code_owner_review` to `true`, and add that person to CODEOWNERS (repo-standards T1.2).
3. **State observed on 2026-10-18** with `scripts/audit_repo_standards.py --online`: `main` has no branch protection and no ruleset (`gh api repos/gasthecreator/vigil/branches/main/protection` returns 404). Applying section 1 is owner action H-GH-1 in `docs/HANDOVER.md`.
