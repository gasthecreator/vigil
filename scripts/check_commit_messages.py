#!/usr/bin/env python3
"""scripts/check_commit_messages.py

Rejects commits whose subject does not follow Conventional Commits
(CONTRIBUTING.md): ``type(scope)!: description`` with type in the allowed set and a description of
at least 10 characters. Merge commits and fixup/revert commits created by git are skipped.

Usage:  python scripts/check_commit_messages.py [BASE]      # checks BASE..HEAD (default origin/main)
Exit 1 and a per-commit list on violation. Used by CI on pull requests.
"""

from __future__ import annotations

import re
import subprocess
import sys

TYPES = "feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert|results"
CC_RE = re.compile(rf"^({TYPES})(\([a-z0-9][a-z0-9._/-]*\))?!?: \S.{{9,}}$")
SKIP_RE = re.compile(r"^(Merge |Revert \"|fixup! |squash! )")


def violations(subjects: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    out = []
    for sha, subj in subjects:
        if SKIP_RE.match(subj):
            continue
        if not CC_RE.match(subj):
            why = "type/scope/colon format" if not re.match(rf"^({TYPES})(\([^)]*\))?!?: ", subj) else "description shorter than 10 characters"
            out.append((sha, subj, why))
    return out


def commits_in_range(base: str) -> list[tuple[str, str]]:
    r = subprocess.run(["git", "log", "--format=%h%x09%s", f"{base}..HEAD"], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git log failed: {r.stderr.strip()}")
    return [tuple(line.split("\t", 1)) for line in r.stdout.splitlines() if "\t" in line]  # type: ignore[misc]


def main(argv: list[str]) -> int:
    base = argv[1] if len(argv) > 1 else "origin/main"
    commits = commits_in_range(base)
    bad = violations(commits)
    print(f"checked {len(commits)} commit(s) in {base}..HEAD")
    for sha, subj, why in bad:
        print(f"  NON-CONFORMING {sha}: {subj!r} ({why})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
