"""The commit-message gate must reject non-conforming subjects and accept conforming ones."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from check_commit_messages import violations  # noqa: E402

GOOD = [
    "feat(api): add urgency ranking endpoint",
    "fix!: reject forged consent bodies on sibling routes",
    "docs: correct phase 8b report",
    "chore(ci): pin setup-uv by commit SHA",
    "Merge branch 'main' into feat/x",
]
BAD = ["wip", "fix", "update stuff", "Feat: capitalised type", "feat(api) missing colon here", "fix: short", "added things to the repo"]


def test_good_subjects_pass():
    assert violations([("a1", s) for s in GOOD]) == []


def test_bad_subjects_are_each_rejected():
    got = violations([("b1", s) for s in BAD])
    assert [s for _, s, _ in got] == BAD
