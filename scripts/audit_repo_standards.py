#!/usr/bin/env python3
"""scripts/audit_repo_standards.py

Repo-standards audit for Vigil that CAN FAIL.

Implements `.agent/skills/repo-standards/references/audit-rubric.md`: every rubric item gets its
own 0-3 score computed from inspection of the repository (git-tracked files, parsed workflow
YAML, parsed config, real command output), with the evidence that produced the score and, when
the score is below 3, the concrete gap. Items that can only be known from GitHub (branch
protection, secret scanning, merged Dependabot PRs, CI history) are scored from `gh api` when
`--online` is given; offline they are recorded as UNVERIFIED and credited 0.

Scoring is never "file exists => points". Where a file is present, its content is checked for the
property the rubric asks about (e.g. every `uses:` pinned, every workflow has permissions, every
ADR has Status/Context/Decision, README commands refer to real targets).

Exit status
  0  every tier reaches its target (Master Plan §12: T0-T4 >= 3.0 avg, T5 >= 2.0 avg) and no critical finding
  1  a tier is below target, or a critical finding exists
  with --critical-only: 1 only for critical findings (used by CI so the gap list is visible but not
  hidden by green-washing and not a permanent red build).

Outputs (written only by this script):  reports/audit/REPO_AUDIT.json  and  docs/audits/REPO-AUDIT-P15.md
(`--write`).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

ROOT_DEFAULT = Path(__file__).resolve().parent.parent
TARGETS = {"T0": 3.0, "T1": 3.0, "T2": 3.0, "T3": 3.0, "T4": 3.0, "T5": 2.0}
TIER_NAMES = {
    "T0": "Foundation",
    "T1": "Collaboration",
    "T2": "Quality gates",
    "T3": "Security & supply chain",
    "T4": "Operations",
    "T5": "Maturity",
}


@dataclass
class Item:
    tier: str
    ident: str
    title: str
    score: int | None  # None => N/A (excluded from the average, reason in `na_reason`)
    evidence: list[str] = field(default_factory=list)
    gap: str = ""
    verified: bool = True  # False => needs GitHub; credited 0
    critical: bool = False
    na_reason: str = ""


# --------------------------------------------------------------------------------------------
class Repo:
    def __init__(self, root: Path, online: bool = False):
        self.root = root
        self.online = online
        self._tracked: list[str] | None = None
        self.owner_repo = self._owner_repo()

    def git(self, *args: str) -> str:
        r = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ""

    @property
    def tracked(self) -> list[str]:
        if self._tracked is None:
            self._tracked = [p for p in self.git("ls-files").splitlines() if p]
        return self._tracked

    def exists(self, rel: str) -> bool:
        return rel in set(self.tracked) or any(t.startswith(rel.rstrip("/") + "/") for t in self.tracked)

    def read(self, rel: str) -> str:
        p = self.root / rel
        try:
            return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
        except OSError:
            return ""

    def glob_tracked(self, pattern: str) -> list[str]:
        import fnmatch

        return [t for t in self.tracked if fnmatch.fnmatch(t, pattern)]

    def _owner_repo(self) -> str | None:
        url = self.git("remote", "get-url", "origin").strip()
        m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
        return m.group(1) if m else None

    def gh(self, *args: str) -> tuple[bool, str]:
        if not self.online:
            return False, "offline"
        try:
            r = subprocess.run(["gh", *args], cwd=self.root, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, str(e)
        return r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr.strip())


def _unverified(tier: str, ident: str, title: str, why: str, gap: str) -> Item:
    return Item(tier, ident, title, 0, [f"UNVERIFIED: {why}"], gap, verified=False)


# ------------------------------------------------------------------------------------- T0
SECRET_RE = re.compile(
    r"(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35})"
)
HAZARD_EXT = (".pem", ".key", ".p12", ".pfx", ".db", ".sqlite", ".sqlite3", ".sql", ".pkl", ".pickle", ".pyc", ".env")


def t0_hazards(r: Repo) -> Item:
    hits = [t for t in r.tracked if t.endswith(HAZARD_EXT) or Path(t).name.startswith(".env") and not t.endswith(".example")]
    secret_hits = []
    big = []
    for t in r.tracked:
        p = r.root / t
        if not p.is_file():
            continue
        if p.stat().st_size > 5_000_000:
            big.append(f"{t} ({p.stat().st_size // 1_000_000} MB)")
            continue
        if p.stat().st_size < 1_000_000 and not t.endswith((".gz", ".png", ".jpg", ".ico", ".woff2", ".lock")):
            try:
                if SECRET_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
                    secret_hits.append(t)
            except OSError:
                pass
    gi = r.read(".gitignore")
    ignore_ok = all(x in gi for x in ("*.db", ".env", "node_modules", "__pycache__"))
    ev = [f"git ls-files scanned: {len(r.tracked)} files", f".gitignore covers db/.env/node_modules/__pycache__: {ignore_ok}"]
    synth = [t for t in r.tracked if t.startswith("data/synthetic/")]
    if synth:
        ev.append(f"tracked data artifacts: {len(synth)} files under data/synthetic/ (synthetic generator output; "
                  "verify none is real patient data: dataset cards in data/dataset_cards/)")
    if hits or secret_hits:
        return Item("T0", "T0.1", "No hazards tracked", 0, ev + [f"hazard files: {hits}", f"secret-pattern files: {secret_hits}"],
                    "Remove from the index and rotate any credential", critical=True)
    score = 3 if ignore_ok and not big else 2
    return Item("T0", "T0.1", "No hazards tracked", score, ev + ([f"files > 5 MB: {big}"] if big else []),
                "" if score == 3 else f"large tracked files {big} or incomplete .gitignore")


def t0_root_clean(r: Repo) -> Item:
    allowed = {
        ".editorconfig", ".gitignore", ".gitleaks.toml", ".gitleaksignore",
        "AGENTS.md", "CHANGELOG.md", "CITATION.cff", "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md", "LICENSE", "NOTICE", "Makefile", "README.md", "SECURITY.md", "conftest.py",
        "package-lock.json", "package.json", "pyproject.toml", "uv.lock", ".python-version", ".nvmrc",
        ".pre-commit-config.yaml", ".gitattributes", "docker-compose.yml", "Dockerfile", ".dockerignore",
        ".env.example", "commitlint.config.cjs", "commitlint.config.js", "release-please-config.json",
        "mkdocs.yml",
    }
    root_files = sorted(t for t in r.tracked if "/" not in t)
    extra = [t for t in root_files if t not in allowed]
    ev = [f"{len(root_files)} tracked root files"]
    gemini = r.read("GEMINI.md")
    if "GEMINI.md" in extra and len(gemini.splitlines()) <= 10 and "AGENTS.md" in gemini:
        ev.append("GEMINI.md is a <=10-line pointer to AGENTS.md (agent-tool shim, accepted)")
        extra.remove("GEMINI.md")
    # untracked clutter on disk that git ignores is not a repo defect but is reported
    untracked = [x for x in ("vigil_dev.db", "quarantine", "__pycache__", ".hypothesis") if (r.root / x).exists()]
    if untracked:
        ev.append(f"present in the working tree but not tracked (ignored or untracked): {untracked}")
    dirs = sorted({t.split("/")[0] for t in r.tracked if "/" in t})
    ev.append(f"tracked top-level dirs: {dirs}")
    if extra:
        return Item("T0", "T0.2", "Root is clean", 1, ev + [f"unexpected tracked root files: {extra}"], f"move or remove {extra}")
    return Item("T0", "T0.2", "Root is clean", 3, ev)


def t0_readme(r: Repo) -> Item:
    txt = r.read("README.md")
    low = txt.lower()
    sections = {"purpose": any(k in low for k in ("what is", "purpose", "vigil is")), "quickstart": "quickstart" in low or "getting started" in low,
                "architecture": "architecture" in low, "status": "status" in low, "disclaimer": "disclaimer" in low or "not a medical device" in low}
    missing = [k for k, v in sections.items() if not v]
    # verify the quickstart: every `make <target>` exists and every script path referenced exists
    mk = r.read("Makefile")
    targets = set(re.findall(r"^([A-Za-z0-9_-]+):", mk, re.M))
    bad = []
    for m in re.findall(r"`?make ([A-Za-z0-9_-]+)", txt):
        if m not in targets:
            bad.append(f"make {m}")
    for pth in set(re.findall(r"(scripts/[A-Za-z0-9_./-]+\.(?:py|sh))", txt)):
        if not r.exists(pth):
            bad.append(pth)
    ev = [f"sections present: {[k for k, v in sections.items() if v]}", f"README `make` targets and script paths checked against Makefile/git ls-files: {len(bad)} dangling"]
    if len(txt) < 500:
        return Item("T0", "T0.3", "README", 1, ev, "README is too short")
    if missing or bad:
        return Item("T0", "T0.3", "README", 1 if len(missing) > 2 else 2, ev + [f"missing sections: {missing}", f"dangling references: {bad}"],
                    "fix the missing sections / dangling quickstart references")
    ev.append("quickstart execution itself is exercised by CI (reproducibility job), not by this audit")
    return Item("T0", "T0.3", "README", 3 if "reproduc" in r.read(".github/workflows/ci.yml").lower() else 2, ev,
                "" if "reproduc" in r.read(".github/workflows/ci.yml").lower() else "no CI job executes the README quickstart from a clean clone")


def t0_license(r: Repo) -> Item:
    lic = r.read("LICENSE")
    ok = "Apache License" in lic and "Version 2.0" in lic and len(lic) > 9000
    py = r.read("pyproject.toml")
    consistent = "Apache" in py or "Apache" in r.read("CITATION.cff") or "apache" in r.read("package.json").lower()
    ev = [f"LICENSE is the full Apache-2.0 text: {ok}", f"license metadata declared in pyproject/CITATION/package.json: {consistent}"]
    if not ok:
        return Item("T0", "T0.4", "LICENSE", 0 if not lic else 1, ev, "LICENSE missing or truncated")
    return Item("T0", "T0.4", "LICENSE", 3 if consistent else 2, ev, "" if consistent else "license not declared in package metadata")


def t0_ignore_editorconfig(r: Repo) -> Item:
    gi = r.read(".gitignore")
    needed = ["__pycache__", ".venv", "node_modules", ".next", "*.db", ".env", ".pytest_cache", ".ruff_cache", ".DS_Store"]
    miss = [n for n in needed if n not in gi]
    ec = r.exists(".editorconfig")
    ev = [f".gitignore missing patterns: {miss}", f".editorconfig tracked: {ec}"]
    s = 3 if not miss and ec else (2 if ec or not miss else 1)
    return Item("T0", "T0.5", ".gitignore and .editorconfig", s, ev, "" if s == 3 else f"missing {miss}, editorconfig={ec}")


def t0_reproducible(r: Repo) -> Item:
    mk = r.read("Makefile")
    targets = set(re.findall(r"^([A-Za-z0-9_-]+):", mk, re.M))
    checks = {
        "uv.lock tracked": r.exists("uv.lock"),
        "package-lock.json tracked": r.exists("package-lock.json"),
        "python version pinned (.python-version or exact requires-python upper bound)": r.exists(".python-version") or "requires-python = \"==" in r.read("pyproject.toml"),
        "node version pinned (.nvmrc or engines)": r.exists(".nvmrc") or '"engines"' in r.read("package.json") or '"engines"' in r.read("apps/web/package.json"),
        "task runner with setup/test/lint": {"setup", "test", "lint"} <= targets,
        "CI installs with frozen lockfiles": "--frozen" in r.read(".github/workflows/ci.yml") or "npm ci" in r.read(".github/workflows/ci.yml"),
    }
    n = sum(checks.values())
    ev = [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()]
    s = 3 if n == len(checks) else 2 if n >= len(checks) - 2 else 1
    gaps = [k for k, v in checks.items() if not v]
    return Item("T0", "T0.6", "Reproducible setup", s, ev, "; ".join(gaps))


def t0_layout(r: Repo) -> Item:
    pkgs = sorted({t.split("/")[1] for t in r.tracked if t.startswith("packages/") and t.count("/") >= 2})
    bad = [p for p in pkgs if not r.exists(f"packages/{p}/pyproject.toml") and not r.exists(f"packages/{p}/package.json")]
    no_tests = [p for p in pkgs if p not in ("contracts", "ui") and not r.glob_tracked(f"packages/{p}/tests/*") and not r.glob_tracked(f"packages/{p}/**/test_*.py")]
    ev = [f"packages: {pkgs}", f"packages without manifest: {bad}", f"python packages without tests: {no_tests}"]
    s = 3 if not bad and not no_tests else 2 if not bad else 1
    return Item("T0", "T0.7", "Layout follows stack convention", s, ev, "" if s == 3 else f"{bad or no_tests}")


# ------------------------------------------------------------------------------------- T1
def t1_governance(r: Repo) -> Item:
    files = ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md"]
    ev, problems = [], []
    for f in files:
        t = r.read(f)
        ev.append(f"{f}: {len(t)} bytes")
        if len(t) < 300:
            problems.append(f"{f} missing/trivial")
        if re.search(r"TODO|FIXME|example\.com|<your|\[INSERT", t, re.I):
            problems.append(f"{f} has placeholder text")
    sec = r.read("SECURITY.md").lower()
    if not any(k in sec for k in ("report", "disclos")) or not re.search(r"@|advisor|mailto|private", sec):
        problems.append("SECURITY.md lacks a reporting channel")
    return Item("T1", "T1.1", "CONTRIBUTING / CODE_OF_CONDUCT / SECURITY", 3 if not problems else 1, ev + [f"problems: {problems}"], "; ".join(problems))


def t1_codeowners(r: Repo) -> Item:
    txt = r.read(".github/CODEOWNERS")
    lines = [ln for ln in txt.splitlines() if ln.strip() and not ln.startswith("#")]
    owners_per_line = [len(re.findall(r"@\S+", ln)) for ln in lines]
    distinct = {o for ln in lines for o in re.findall(r"@\S+", ln)}
    two_plus = sum(1 for n in owners_per_line if n >= 2)
    wf = any(".github" in ln for ln in lines)
    ev = [f"{len(lines)} rules, distinct owners: {sorted(distinct)}", f"rules with >=2 owners: {two_plus}/{len(lines)}", f"workflows owned: {wf}"]
    if not lines:
        return Item("T1", "T1.2", "CODEOWNERS", 0, ev, "no CODEOWNERS")
    if len(distinct) < 2:
        return Item("T1", "T1.2", "CODEOWNERS", 1, ev, "single owner for everything: no independent reviewer exists for safety-critical paths (rubric asks 2+ owners per critical area)")
    return Item("T1", "T1.2", "CODEOWNERS", 3 if two_plus == len(lines) and wf else 2, ev)


def t1_templates(r: Repo) -> Item:
    pr = r.read(".github/PULL_REQUEST_TEMPLATE.md")
    issues = [t for t in r.tracked if t.startswith(".github/ISSUE_TEMPLATE/")]
    ev = [f"PR template {len(pr)} bytes; checklist items: {pr.count('- [ ]')}", f"issue templates: {issues}"]
    s = 3 if pr.count("- [ ]") >= 3 and len(issues) >= 2 else 2 if pr and issues else 1 if pr or issues else 0
    return Item("T1", "T1.3", "Issue and PR templates", s, ev, "" if s == 3 else "templates incomplete")


CC_RE = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+")


def t1_conventional(r: Repo) -> Item:
    wfs = " ".join(r.read(t) for t in r.tracked if t.startswith(".github/workflows/"))
    cfg = [t for t in r.tracked if "commitlint" in t.lower()] or ([".pre-commit-config.yaml"] if "conventional" in r.read(".pre-commit-config.yaml").lower() else [])
    ci = bool(re.search(r"commitlint|conventional-pre-commit|semantic-pull-request|action-semantic", wfs, re.I))
    ev = [f"commit-message lint config tracked: {cfg}", f"CI step that enforces it: {ci}", "convention documented: " + str("conventional" in r.read("CONTRIBUTING.md").lower())]
    s = 3 if cfg and ci else 1 if "conventional" in r.read("CONTRIBUTING.md").lower() else 0
    return Item("T1", "T1.4", "Conventional Commits enforced", s, ev,
                "" if s == 3 else "convention is documented but nothing rejects a non-conforming commit/PR title" if s else "no convention and no enforcement")


def t1_history(r: Repo) -> Item:
    msgs = [m for m in r.git("log", "-n", "300", "--format=%s", "origin/main" if r.git("rev-parse", "--verify", "origin/main").strip() else "HEAD").splitlines() if m]
    if not msgs:
        return Item("T1", "T1.5", "History readable", None, [], na_reason="no git history available")
    bad_re = re.compile(r"^(wip|fix|update|stuff|changes?|\.|asdf|tmp|test)$", re.I)
    cc = sum(1 for m in msgs if CC_RE.match(m))
    bad = [m for m in msgs if bad_re.match(m.strip())]
    short = [m for m in msgs if len(m) < 10]
    ev = [f"last {len(msgs)} commit subjects: {cc} conventional ({100*cc//len(msgs)}%), {len(bad)} throwaway, {len(short)} <10 chars"]
    frac = cc / len(msgs)
    s = 3 if frac >= 0.9 and not bad else 2 if frac >= 0.6 and len(bad) <= 2 else 1 if frac >= 0.3 else 0
    return Item("T1", "T1.5", "History readable", s, ev, "" if s == 3 else f"only {100*frac:.0f}% of commit subjects are conventional; examples of non-conforming: {[m for m in msgs if not CC_RE.match(m)][:3]}")


def t1_branch_protection(r: Repo) -> Item:
    t = "Default branch protected (PR-only, required checks, review, no force-push)"
    if not r.online or not r.owner_repo:
        return _unverified("T1", "T1.6", t, "needs GitHub API; run with --online", "run with --online or apply docs/ops/GITHUB-SETTINGS.md and verify")
    ok, out = r.gh("api", f"repos/{r.owner_repo}/branches/main/protection")
    if not ok:
        rs_ok, rs = r.gh("api", f"repos/{r.owner_repo}/rulesets")
        has_rs = rs_ok and rs.strip() not in ("", "[]")
        if has_rs:
            return Item("T1", "T1.6", t, 2, [f"branch protection API: {out[:120]}", "a ruleset exists: " + rs[:200]], "ruleset contents not parsed by this audit")
        return Item("T1", "T1.6", t, 0, [f"gh api branches/main/protection -> {out[:160]}", "no rulesets"], "main is not protected on GitHub (owner action: docs/ops/GITHUB-SETTINGS.md)")
    d = json.loads(out)
    checks = {
        "required status checks": bool(d.get("required_status_checks")),
        "required PR review": bool(d.get("required_pull_request_reviews")),
        "force pushes blocked": not d.get("allow_force_pushes", {}).get("enabled", True),
        "admins enforced": bool(d.get("enforce_admins", {}).get("enabled")),
    }
    n = sum(checks.values())
    return Item("T1", "T1.6", t, 3 if n == 4 else 2 if n >= 3 else 1, [f"{k}: {v}" for k, v in checks.items()], "" if n == 4 else str([k for k, v in checks.items() if not v]))


# ------------------------------------------------------------------------------------- T2
def _ci(r: Repo) -> str:
    return r.read(".github/workflows/ci.yml")


def t2_lint(r: Repo) -> Item:
    ci = _ci(r)
    checks = {"ruff check in CI": "ruff check" in ci, "ruff format --check in CI": "ruff format --check" in ci or "ruff format" in ci,
              "eslint in CI": bool(re.search(r"web:lint|npm run lint|eslint", ci)), "type check in CI (mypy/pyright/tsc)": bool(re.search(r"mypy|pyright|tsc", ci))}
    n = sum(checks.values())
    return Item("T2", "T2.1", "Formatter and linter enforced in CI", 3 if n == 4 else 2 if n >= 2 else 1 if n else 0, [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()],
                "; ".join(f"missing: {k}" for k, v in checks.items() if not v))


def t2_unit(r: Repo) -> Item:
    files = [t for t in r.tracked if re.search(r"(^|/)test_[^/]*\.py$", t)]
    n_tests = neg = 0
    for f in files:
        txt = r.read(f)
        n_tests += len(re.findall(r"^\s*(?:async )?def test_", txt, re.M))
        neg += len(re.findall(r"pytest\.raises|status_code == 4\d\d|status_code in \(4|assert .* is False|== 403|== 401|== 422", txt))
    ratio = neg / max(n_tests, 1)
    ev = [f"{len(files)} python test files, {n_tests} test functions", f"{neg} failure-path assertions (raises / 4xx / is False) => {ratio:.2f} per test"]
    s = 3 if ratio >= 0.2 and n_tests >= 300 else 2 if ratio >= 0.1 else 1
    return Item("T2", "T2.2", "Unit tests cover behaviour and failure paths", s, ev, "" if s == 3 else "few failure-path assertions relative to test count")


def t2_integration(r: Repo) -> Item:
    ci = _ci(r)
    e2e = r.glob_tracked("apps/web/e2e/*.spec.ts")
    acc = {t.split("/")[1] for t in r.tracked if t.startswith("tests/acceptance_")}
    checks = {"playwright e2e in CI": "playwright" in ci, "acceptance suites run in CI": "tests/acceptance" in ci or "acceptance" in ci, "e2e specs": len(e2e) >= 3,
              "security suite in CI": "tests/security" in ci or "pytest" in ci and "tests/" in ci, "lighthouse in CI": "lighthouse" in ci.lower() or "lhci" in ci.lower()}
    n = sum(checks.values())
    ev = [f"{len(e2e)} e2e specs; {len(acc)} acceptance suites"] + [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()]
    return Item("T2", "T2.3", "Integration/e2e for critical flows", 3 if n == 5 else 2 if n >= 3 else 1, ev, "; ".join(f"missing: {k}" for k, v in checks.items() if not v))


def t2_flakes_speed(r: Repo) -> Item:
    t = "Flakes tracked; presubmit CI under ~10 min"
    flake_doc = [x for x in r.tracked if "flake" in x.lower()] or (["docs mention"] if re.search(r"flak", r.read("CONTRIBUTING.md"), re.I) else [])
    ev = [f"flake tracking artifact/policy: {flake_doc}"]
    if r.online and r.owner_repo:
        ok, out = r.gh("run", "list", "--workflow", "ci.yml", "--branch", "main", "--limit", "20", "--json", "createdAt,updatedAt,conclusion,startedAt")
        if ok:
            from datetime import datetime

            runs = json.loads(out)
            durs = []
            for x in runs:
                if x.get("conclusion") == "success" and x.get("startedAt"):
                    a = datetime.fromisoformat(x["startedAt"].replace("Z", "+00:00"))
                    b = datetime.fromisoformat(x["updatedAt"].replace("Z", "+00:00"))
                    durs.append((b - a).total_seconds() / 60)
            if durs:
                durs.sort()
                med = durs[len(durs) // 2]
                ev.append(f"median CI wall time over {len(durs)} successful main runs: {med:.1f} min")
                s = (2 if med <= 10 else 1) + (1 if flake_doc and med <= 10 else 0)
                return Item("T2", "T2.4", t, s, ev, "" if s == 3 else ("CI median > 10 min" if med > 10 else "no flake tracking"))
        ev.append(f"gh run list unavailable: {out[:100]}")
    else:
        ev.append("UNVERIFIED: CI duration needs --online")
    return Item("T2", "T2.4", t, 1 if flake_doc else 0, ev, "CI duration unverified offline" + ("" if flake_doc else "; no flake tracking"), verified=False)


def t2_coverage(r: Repo) -> Item:
    ci = _ci(r)
    pyp = r.read("pyproject.toml")
    checks = {"coverage measured in CI (--cov)": "--cov" in ci or "coverage run" in ci, "threshold/ratchet (fail_under / --cov-fail-under)": "fail_under" in pyp or "cov-fail-under" in ci or "fail_under" in r.read(".coveragerc"),
              "report published as artifact/summary": "coverage.xml" in ci or "codecov" in ci.lower() or "upload-artifact" in ci}
    n = sum(checks.values())
    return Item("T2", "T2.5", "Coverage reported as a signal", n, [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()],
                "; ".join(f"missing: {k}" for k, v in checks.items() if not v))


def t2_property(r: Repo) -> Item:
    uses = {t: len(re.findall(r"@given", r.read(t))) for t in r.tracked if re.search(r"(^|/)test_[^/]*\.py$", t) and "@given" in r.read(t)}
    parsers = [t for t in r.tracked if re.search(r"(loader|parser|ingest|import)", t, re.I) and t.endswith(".py") and "/tests/" not in t and not Path(t).name.startswith("test_") and not t.endswith("__init__.py")]
    total = sum(uses.values())
    ev = [f"{total} @given property tests across {len(uses)} files", f"input-parsing modules: {parsers[:6]}"]
    covered = [p for p in parsers if any(Path(p).stem in r.read(t) for t in uses)]
    s = 3 if total >= 10 and (not parsers or len(covered) >= max(1, len(parsers) // 2)) else 2 if total >= 3 else 1 if total else 0
    return Item("T2", "T2.6", "Fuzz/property tests where input is parsed", s, ev, "" if s == 3 else "parsing modules without property/fuzz tests: " + str([p for p in parsers if p not in covered][:6]))


def t2_ci_green(r: Repo) -> Item:
    t = "CI green on default branch; badge honest"
    badges = re.findall(r"actions/workflows/([A-Za-z0-9_.-]+)/badge", r.read("README.md"))
    bad_badges = [b for b in badges if not r.exists(f".github/workflows/{b}")]
    ev = [f"README workflow badges: {badges}; pointing at missing workflows: {bad_badges}"]
    if not r.online or not r.owner_repo:
        return Item("T2", "T2.7", t, 0, ev + ["UNVERIFIED: default-branch CI state needs --online"], "run with --online", verified=False)
    ok, out = r.gh("run", "list", "--workflow", "ci.yml", "--branch", "main", "--limit", "1", "--json", "conclusion,headSha,status")
    if not ok or not json.loads(out or "[]"):
        return Item("T2", "T2.7", t, 0, ev + [f"no CI run on main found: {out[:100]}"], "CI has not run on main")
    run = json.loads(out)[0]
    ev.append(f"latest ci.yml run on main: {run}")
    s = 3 if run.get("conclusion") == "success" and not bad_badges else 1
    return Item("T2", "T2.7", t, s, ev, "" if s == 3 else "latest main run not successful or badge dishonest")


# ------------------------------------------------------------------------------------- T3
def _workflows(r: Repo) -> dict[str, str]:
    return {t: r.read(t) for t in r.tracked if t.startswith(".github/workflows/") and t.endswith((".yml", ".yaml"))}


def t3_secret_scanning(r: Repo) -> Item:
    t = "Secret scanning and push protection"
    wf = " ".join(_workflows(r).values()).lower()
    ci_scan = any(k in wf for k in ("gitleaks", "trufflehog", "detect-secrets"))
    ev = [f"secret-scan step in CI: {ci_scan}"]
    if r.online and r.owner_repo:
        ok, out = r.gh("api", f"repos/{r.owner_repo}")
        if ok:
            sa = json.loads(out).get("security_and_analysis") or {}
            ss = (sa.get("secret_scanning") or {}).get("status")
            pp = (sa.get("secret_scanning_push_protection") or {}).get("status")
            ev.append(f"GitHub secret_scanning={ss}, push_protection={pp}")
            s = (1 if ss == "enabled" else 0) + (1 if pp == "enabled" else 0) + (1 if ci_scan else 0)
            return Item("T3", "T3.1", t, s, ev, "" if s == 3 else "enable GitHub secret scanning + push protection and add a CI secret scan")
        ev.append(f"repo API unavailable: {out[:100]}")
    return Item("T3", "T3.1", t, 1 if ci_scan else 0, ev + ["UNVERIFIED: GitHub-side settings need --online"], "no CI secret scan" if not ci_scan else "GitHub settings unverified", verified=False)


def t3_sast_vuln(r: Repo) -> Item:
    wf = " ".join(_workflows(r).values()).lower()
    checks = {"CodeQL analysis workflow (github/codeql-action/analyze)": "codeql-action/analyze" in wf,
              "python dependency audit (pip-audit/osv-scanner/safety)": bool(re.search(r"pip-audit|osv-scanner|safety check", wf)),
              "npm audit / osv for web": bool(re.search(r"npm audit|osv-scanner", wf)),
              "static analysis other than ruff (bandit/semgrep)": bool(re.search(r"bandit|semgrep", wf) or "bandit" in r.read("pyproject.toml"))}
    n = sum(checks.values())
    return Item("T3", "T3.2", "SAST and dependency vulnerability scanning", min(3, n), [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()],
                "; ".join(f"missing: {k}" for k, v in checks.items() if not v))


def t3_dependabot(r: Repo) -> Item:
    t = "Dependabot/Renovate configured and PRs merged"
    cfg = r.read(".github/dependabot.yml")
    eco = set(re.findall(r"package-ecosystem:\s*([\w-]+)", cfg))
    need = {"github-actions", "npm", "pip"}
    ev = [f"ecosystems configured: {sorted(eco)}; missing: {sorted(need - eco)}"]
    base = 2 if need <= eco else 1 if eco else 0
    if r.online and r.owner_repo:
        ok, out = r.gh("pr", "list", "--state", "merged", "--search", "author:app/dependabot", "--limit", "50", "--json", "number")
        if ok:
            n = len(json.loads(out or "[]"))
            ev.append(f"merged Dependabot PRs found: {n}")
            return Item("T3", "T3.3", t, 3 if base == 2 and n > 0 else base, ev, "" if base == 2 and n > 0 else "no merged Dependabot PRs: automation is configured but its output is not being consumed" if base == 2 else "")
    return Item("T3", "T3.3", t, min(base, 2) if base < 2 else 1, ev + ["UNVERIFIED: merged-PR history needs --online (configured but unproven)"], "merged Dependabot PRs unverified", verified=False)


def t3_actions(r: Repo) -> Item:
    wfs = _workflows(r)
    unpinned, no_perm, dangerous, writes, remote_scripts = [], [], [], [], []
    total_uses = 0
    for name, txt in wfs.items():
        for m in re.finditer(r"uses:\s*([^\s#]+)", txt):
            ref = m.group(1)
            if ref.startswith("./"):
                continue
            total_uses += 1
            if "@" not in ref or not re.fullmatch(r"[0-9a-f]{40}", ref.split("@", 1)[1]):
                unpinned.append(f"{name}: {ref}")
        if not re.search(r"^permissions:", txt, re.M):
            no_perm.append(name)
        if "permissions: write-all" in txt:
            writes.append(name)
        if re.search(r"pull_request_target|workflow_run", txt):
            dangerous.append(name)
        if re.search(r"curl[^\n|]*\|\s*(sh|bash)", txt):
            remote_scripts.append(name)
    ev = [f"{len(wfs)} workflows, {total_uses} third-party `uses:`", f"unpinned: {unpinned}", f"no top-level permissions: {no_perm}", f"write-all: {writes}", f"risky triggers: {dangerous}", f"unpinned remote scripts piped to a shell (curl | sh): {remote_scripts}"]
    bad = bool(unpinned or no_perm or writes or dangerous or remote_scripts)
    return Item("T3", "T3.4", "Actions pinned to SHAs; least privilege; no dangerous triggers", 3 if not bad else 1 if len(unpinned) + len(no_perm) > 3 else 2, ev, "" if not bad else "see evidence lists (curl | sh installs of uv are not integrity-checked: pin via astral-sh/setup-uv by SHA)", critical=bool(dangerous or writes))


def t3_threat_model(r: Repo) -> Item:
    t = r.read("docs/security/THREAT_MODEL.md")
    parts = {"assets": "asset" in t.lower(), "trust boundaries": "boundar" in t.lower(), "threats (STRIDE or equivalent)": bool(re.search(r"spoof|tamper|repudiat|disclos|denial|elevation", t, re.I)),
             "mitigations mapped to tests/code": bool(re.search(r"tests/|apps/|scripts/", t)), "review date": bool(re.search(r"20\d\d-\d\d-\d\d", t))}
    n = sum(parts.values())
    return Item("T3", "T3.5", "Threat model", 0 if not t else 3 if n == 5 else 2 if n >= 4 else 1, [f"{len(t)} bytes"] + [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in parts.items()],
                "" if n == 5 else "; ".join(f"missing: {k}" for k, v in parts.items() if not v))


def t3_sbom_signing(r: Repo) -> Item:
    sboms = [t for t in r.tracked if t.startswith("reports/sbom/") and t.endswith(".json")]
    valid = 0
    for s in sboms:
        try:
            d = json.loads(r.read(s))
            valid += d.get("bomFormat") == "CycloneDX" and bool(d.get("components"))
        except json.JSONDecodeError:
            pass
    wf = " ".join(_workflows(r).values()).lower()
    sigs = [t for t in r.tracked if t.endswith((".minisig", ".sig", ".asc")) or "attestation" in t.lower()]
    sign_ci = bool(re.search(r"attest-build-provenance|slsa-github-generator|cosign|minisign|sigstore", wf))
    tags = r.git("tag", "-l").split()
    ev = [f"CycloneDX SBOMs parsed with components: {valid}/{len(sboms)}", f"signatures/attestations tracked: {sigs}", f"signing/provenance in CI: {sign_ci}", f"git tags: {tags[:5]}"]
    s = (1 if valid else 0) + (1 if sign_ci or sigs else 0) + (1 if sign_ci and sigs else 0)
    return Item("T3", "T3.6", "SBOM and signed releases/provenance", s, ev, "" if s == 3 else "no signed/attested release artifact exists: the release manifest is a hash manifest only (owner action: generate signing key, see docs/release/SIGNING.md)")


def t3_scorecard(r: Repo) -> Item:
    wf = r.read(".github/workflows/scorecard.yml")
    ok = "ossf/scorecard-action" in wf and "publish_results" in wf
    recorded = [t for t in r.tracked if "scorecard" in t.lower() and t.endswith((".json", ".sarif", ".md")) and "workflows" not in t]
    ev = [f"scorecard workflow with publish_results: {ok}", f"recorded score artifact: {recorded}"]
    return Item("T3", "T3.7", "Scorecard run in CI; score tracked", 0 if not wf else 3 if ok and recorded else 2 if ok else 1, ev, "" if ok and recorded else "no recorded score / target (Master Plan: >= 8)")


# ------------------------------------------------------------------------------------- T4
def t4_observability(r: Repo) -> Item:
    api = "\n".join(r.read(t) for t in r.tracked if t.startswith("apps/api/vigil_api/") and t.endswith(".py"))
    checks = {"structured (JSON) logging": bool(re.search(r"logger\.\w+\(\s*json\.dumps|JSONFormatter|structlog", api)),
              "request id correlation": "request_id" in api, "health endpoints": bool(re.search(r"/health|/ready|/live", api)),
              "metrics endpoint": bool(re.search(r"/metrics|prometheus", api, re.I)), "tracing (OpenTelemetry)": "opentelemetry" in api.lower()}
    n = sum(checks.values())
    return Item("T4", "T4.1", "Structured logging, metrics, tracing, health", 3 if n == 5 else 2 if n >= 3 else 1 if n else 0, [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()],
                "; ".join(f"missing: {k}" for k, v in checks.items() if not v))


def t4_config(r: Repo) -> Item:
    api = "\n".join(r.read(t) for t in r.tracked if t.startswith("apps/api/vigil_api/") and t.endswith(".py"))
    env_vars = sorted(set(re.findall(r"(?:getenv|environ\.get|environ\[)\(?\s*[\"']([A-Z][A-Z0-9_]+)[\"']", api)) - {"OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"})
    example = r.read(".env.example")
    documented = [v for v in env_vars if v in example or v in r.read("docs/deployment/ON_PREM_INSTALL.md")]
    ev = [f"{len(env_vars)} VIGIL_* environment variables read by the API", f".env.example tracked: {bool(example)}", f"documented (in .env.example or install guide): {len(documented)}/{len(env_vars)}"]
    s = 3 if example and len(documented) == len(env_vars) else 2 if len(documented) >= len(env_vars) // 2 and env_vars else 1 if env_vars else 0
    return Item("T4", "T4.2", "Config via environment; .env.example", s, ev, "" if s == 3 else f"undocumented variables: {[v for v in env_vars if v not in documented]}; .env.example {'present' if example else 'absent'}")


def t4_runbooks_slo(r: Repo) -> Item:
    rb = [t for t in r.tracked if t.startswith("docs/runbooks/")]
    slo = [t for t in r.tracked if re.search(r"slo", t, re.I)] or [t for t in r.tracked if t.endswith(".md") and re.search(r"\bSLO\b", r.read(t))]
    alerts = [t for t in r.tracked if re.search(r"alert", t, re.I)]
    ev = [f"runbooks: {rb}", f"SLO documents: {slo[:4]}", f"alert definitions: {alerts[:4]}"]
    s = (1 if len(rb) >= 1 else 0) + (1 if len(rb) >= 3 else 0) + (1 if slo else 0)
    s = min(3, s)
    return Item("T4", "T4.3", "Runbooks linked to alerts; SLOs defined", s, ev, "" if s == 3 else f"{len(rb)} runbook(s); {'no' if not slo else ''} SLO doc; alert->runbook linkage {'absent' if not alerts else 'present'}")


def t4_release_rollback(r: Repo) -> Item:
    rel_docs = [t for t in r.tracked if t.startswith("docs/release/")]
    mig = [t for t in r.tracked if "alembic/versions/" in t and t.endswith(".py")]
    down = sum(1 for t in mig if re.search(r"def downgrade\(\)[^:]*:\s*\n(?!\s*pass\s*$)", r.read(t)))
    mig_tests = [t for t in r.tracked if re.search(r"(test_.*migrat|test_.*rollback|test_.*upgrade)", t)]
    ev = [f"release docs: {rel_docs[:5]}", f"{len(mig)} alembic migrations, {down} with a non-trivial downgrade", f"migration/rollback tests: {mig_tests}"]
    s = (1 if rel_docs else 0) + (1 if mig and down >= len(mig) else 0) + (1 if mig_tests else 0)
    return Item("T4", "T4.4", "Release process; rollback tested; migrations compatible", s, ev, "" if s == 3 else "rollback not exercised by any test" if not mig_tests else "some migrations lack downgrade")


def t4_docker(r: Repo) -> Item:
    dfs = [t for t in r.tracked if Path(t).name.startswith("Dockerfile")]
    if not dfs:
        return Item("T4", "T4.5", "Dockerfile hardened", 0, ["no Dockerfile tracked (on-prem install is a Python installer script)"],
                    "no container image definition (Master Plan WP0.4 lists Docker/compose); installer-only distribution")
    txt = "\n".join(r.read(d) for d in dfs)
    checks = {"multi-stage": len(re.findall(r"^FROM ", txt, re.M)) >= 2, "non-root USER": bool(re.search(r"^USER (?!root)", txt, re.M)),
              "pinned base (digest or exact tag)": bool(re.search(r"^FROM \S+(@sha256:|:\d)", txt, re.M)), "HEALTHCHECK": "HEALTHCHECK" in txt}
    n = sum(checks.values())
    return Item("T4", "T4.5", "Dockerfile hardened", {4: 3, 3: 2, 2: 1}.get(n, 0), [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()], "")


def t4_incident(r: Repo) -> Item:
    f = [t for t in r.tracked if re.search(r"(postmortem|post-mortem|incident)", t, re.I) and t.endswith(".md")]
    return Item("T4", "T4.6", "Incident/postmortem template", 3 if f else 0, [f"templates: {f}"], "" if f else "no incident/postmortem template")


# ------------------------------------------------------------------------------------- T5
def _adr_complete(txt: str) -> bool:
    low = txt.lower()
    has_status = bool(re.search(r"^status:|^## status", low, re.M))
    return has_status and "context" in low and "decision" in low


def t5_adrs(r: Repo) -> Item:
    adrs = sorted(t for t in r.tracked if re.fullmatch(r"docs/adr/\d{4}-.*\.md", t))
    nums = Counter(Path(a).name[:4] for a in adrs)
    dup = [n for n, c in nums.items() if c > 1]
    ints = sorted(int(n) for n in nums)
    gaps = [i for i in range(ints[0], ints[-1] + 1) if i not in ints] if ints else []
    incomplete = [a for a in adrs if not _adr_complete(r.read(a))]
    ev = [f"{len(adrs)} ADRs; duplicate numbers: {dup}; numbering gaps: {gaps}", f"missing Status/Context/Decision: {incomplete}"]
    s = 3 if len(adrs) >= 15 and not dup and not incomplete else 2 if len(adrs) >= 8 and not incomplete else 1
    return Item("T5", "T5.1", "ADRs for significant decisions", s, ev, "" if s == 3 else f"duplicates {dup}, incomplete {incomplete}")


def t5_docs(r: Repo) -> Item:
    try:
        p = subprocess.run([sys.executable, str(r.root / "scripts/check_docs_links.py")], cwd=r.root, capture_output=True, text=True, timeout=300)
        link_ok, tail = p.returncode == 0, (p.stdout.strip().splitlines() or [""])[-1]
    except (OSError, subprocess.TimeoutExpired) as e:
        link_ok, tail = False, str(e)
    index = r.exists("docs/README.md") or r.exists("docs/index.md")
    canon = all(r.exists(x) for x in ("docs/MASTER_PLAN.md", "docs/PROGRESS.md", "docs/EVIDENCE.md"))
    ev = [f"link checker passes: {link_ok} ({tail})", f"docs index present: {index}", f"canonical docs present: {canon}"]
    s = (1 if link_ok else 0) + (1 if index else 0) + (1 if canon else 0)
    return Item("T5", "T5.2", "Docs organised by reader need; canonical; fresh", s, ev, "" if s == 3 else "docs index missing" if not index else "")


def t5_changelog(r: Repo) -> Item:
    ch = r.read("CHANGELOG.md")
    tags = r.git("tag", "-l").split()
    semver_tags = [t for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+(-[\w.]+)?", t)]
    ev = [f"CHANGELOG has Unreleased: {'Unreleased' in ch}; release headings: {len(re.findall(r'^## \[?\d', ch, re.M))}", f"SemVer git tags: {semver_tags}", f"release notes docs: {[t for t in r.tracked if 'release' in t.lower() and t.endswith('.md')][:4]}"]
    s = (1 if "Unreleased" in ch else 0) + (1 if re.search(r"^## \[?\d", ch, re.M) else 0) + (1 if semver_tags else 0)
    return Item("T5", "T5.3", "CHANGELOG + SemVer tags + release notes", s, ev, "" if s == 3 else "no SemVer tag exists: the release candidate has never been tagged" if not semver_tags else "")


def t5_deprecation(r: Repo) -> Item:
    f = [t for t in r.tracked if t.endswith(".md") and re.search(r"deprecat|compatib|versioning policy", r.read(t), re.I) and t.startswith(("docs/", "CONTRIBUTING", "SECURITY"))]
    policy = [t for t in f if re.search(r"deprecation policy|compatibility policy|## Deprecat", r.read(t), re.I)]
    return Item("T5", "T5.4", "Deprecation and compatibility policy", 3 if policy else 1 if f else 0, [f"documents mentioning deprecation/compat: {f[:4]}", f"documents with an explicit policy section: {policy}"],
                "" if policy else "no explicit deprecation/compatibility policy section")


def t5_bench(r: Repo) -> Item:
    load = [t for t in r.tracked if t.startswith("reports/load/") and t.endswith(".json")]
    transports = {}
    for t in load:
        try:
            d = json.loads(r.read(t))
            transports[t] = d.get("transport") or d.get("metadata", {}).get("transport") or "unspecified"
        except json.JSONDecodeError:
            transports[t] = "unparseable"
    http = [t for t, v in transports.items() if v == "http"]
    fault = [t for t in r.tracked if t.startswith("tests/resilience/") and t.endswith(".py")]
    ev = [f"load results: {transports}", f"fault/resilience test files: {len(fault)}"]
    s = (1 if load else 0) + (1 if http else 0) + (1 if fault else 0)
    return Item("T5", "T5.5", "Benchmarks/load results committed; fault tests", s, ev, "" if s == 3 else "no committed load result declares transport=http (real-network measurement)" if not http else "")


def t5_openssf_dora(r: Repo) -> Item:
    docs = " ".join(r.read(t) for t in r.tracked if t.endswith(".md") and t.startswith(("docs/", "README")))
    badge = "bestpractices.dev" in docs or "openssf best practices" in docs.lower()
    dora = bool(re.search(r"\bDORA\b|deployment frequency|lead time", docs, re.I))
    return Item("T5", "T5.6", "OpenSSF Best Practices progress; DORA observed", int(badge) + int(dora) + (1 if badge and dora else 0), [f"OpenSSF Best Practices referenced: {badge}", f"DORA metrics referenced: {dora}"],
                "" if badge and dora else "no OpenSSF Best Practices registration and no DORA measurement (both need a running project on GitHub)")


CHECKS: list[Callable[[Repo], Item]] = [
    t0_hazards, t0_root_clean, t0_readme, t0_license, t0_ignore_editorconfig, t0_reproducible, t0_layout,
    t1_governance, t1_codeowners, t1_templates, t1_conventional, t1_history, t1_branch_protection,
    t2_lint, t2_unit, t2_integration, t2_flakes_speed, t2_coverage, t2_property, t2_ci_green,
    t3_secret_scanning, t3_sast_vuln, t3_dependabot, t3_actions, t3_threat_model, t3_sbom_signing, t3_scorecard,
    t4_observability, t4_config, t4_runbooks_slo, t4_release_rollback, t4_docker, t4_incident,
    t5_adrs, t5_docs, t5_changelog, t5_deprecation, t5_bench, t5_openssf_dora,
]


def run_audit(root: Path, online: bool) -> dict:
    r = Repo(root, online)
    items = [c(r) for c in CHECKS]
    tiers = {}
    for t in TARGETS:
        scored = [i for i in items if i.tier == t and i.score is not None]
        avg = sum(i.score for i in scored) / len(scored) if scored else 0.0
        tiers[t] = {"name": TIER_NAMES[t], "average": round(avg, 2), "target": TARGETS[t], "met": avg >= TARGETS[t], "items": len(scored)}
    return {"online": online, "repo": r.owner_repo, "head": r.git("rev-parse", "--short", "HEAD").strip(), "tiers": tiers,
            "critical": [i.ident for i in items if i.critical], "items": [asdict(i) for i in items]}


def render_markdown(res: dict) -> str:
    L = [f"# Repo-standards audit (rubric T0-T5) — commit `{res['head']}`", "",
         "> Written by `scripts/audit_repo_standards.py --write`. Do not edit by hand. Scores come from inspecting the repository; they are not self-awarded.",
         f"> Mode: {'online (GitHub API consulted)' if res['online'] else 'offline (GitHub-side items UNVERIFIED and credited 0)'}.", "",
         "Supersedes `REPO-AUDIT-P8B.md`, whose 3.00/3.00 was awarded for file presence (VERDICT-P8B defect 5).", "",
         "## Scorecard (Master Plan §12 target: T0-T4 average >= 3, T5 >= 2)", "", "| Tier | Average | Target | Result |", "|---|---:|---:|---|"]
    for t, d in res["tiers"].items():
        L.append(f"| {t} {d['name']} | {d['average']:.2f} | {d['target']:.1f} | {'MET' if d['met'] else '**NOT MET**'} |")
    unmet = [t for t, d in res["tiers"].items() if not d["met"]]
    L += ["", f"**Overall: {'all targets met' if not unmet else 'targets NOT met for ' + ', '.join(unmet)}.** Critical findings: {res['critical'] or 'none'}.", "", "## Items", ""]
    for t in TARGETS:
        L += [f"### {t} {TIER_NAMES[t]}", "", "| Item | Score | Evidence | Gap |", "|---|:-:|---|---|"]
        for i in res["items"]:
            if i["tier"] != t:
                continue
            sc = "N/A" if i["score"] is None else f"{i['score']}/3" + ("" if i["verified"] else " (unverified)")
            ev = "<br>".join(e.replace("|", "\\|") for e in i["evidence"])
            L.append(f"| {i['ident']} {i['title']} | {sc} | {ev} | {(i['gap'] or i['na_reason'] or '—').replace('|', chr(92) + '|')} |")
        L.append("")
    L += ["## Gap list (items scoring < 3, ranked low score first)", ""]
    gaps = sorted((i for i in res["items"] if i["score"] is not None and i["score"] < 3), key=lambda i: i["score"])
    for i in gaps:
        L.append(f"- **{i['ident']} {i['title']}** ({i['score']}/3): {i['gap']}")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    ap.add_argument("--online", action="store_true", help="consult GitHub through the gh CLI (read-only)")
    ap.add_argument("--write", action="store_true", help="write reports/audit/REPO_AUDIT.json and docs/audits/REPO-AUDIT-P15.md")
    ap.add_argument("--critical-only", action="store_true", help="exit 1 only for critical findings (CI mode)")
    a = ap.parse_args(argv)
    res = run_audit(a.root, a.online)
    for t, d in res["tiers"].items():
        print(f"{t} {d['name']:<26} {d['average']:.2f} / target {d['target']:.1f}  {'MET' if d['met'] else 'NOT MET'}")
    for i in res["items"]:
        if i["score"] is not None and i["score"] < 3:
            print(f"  gap {i['ident']} ({i['score']}/3){'' if i['verified'] else ' [unverified]'}: {i['gap']}")
    if res["critical"]:
        print("CRITICAL:", res["critical"])
    if a.write:
        out = a.root / "reports" / "audit"
        out.mkdir(parents=True, exist_ok=True)
        (out / "REPO_AUDIT.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (a.root / "docs" / "audits" / "REPO-AUDIT-P15.md").write_text(render_markdown(res), encoding="utf-8")
    if res["critical"]:
        return 1
    if a.critical_only:
        return 0
    return 0 if all(d["met"] for d in res["tiers"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
