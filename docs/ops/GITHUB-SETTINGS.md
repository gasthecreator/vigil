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
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          {"context": "lint-and-typecheck"},
          {"context": "unit-and-property-tests"},
          {"context": "claims-policy-check"}
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
  - `lint-and-typecheck`
  - `unit-and-property-tests`
  - `claims-policy-check`
- [ ] CODEOWNERS review is required.
- [ ] Secret scanning and Dependabot alerts are active.
