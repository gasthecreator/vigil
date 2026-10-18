"""The repo-standards audit must be able to fail, and must fail for the right reasons."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import audit_repo_standards as audit  # noqa: E402


def _git_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "chore: seed"], cwd=tmp_path, check=True)
    return tmp_path


def test_empty_repo_fails_every_tier(tmp_path):
    root = _git_repo(tmp_path, {"README.md": "x"})
    res = audit.run_audit(root, online=False)
    assert all(not t["met"] for t in res["tiers"].values())
    assert audit.main(["--root", str(root)]) == 1


def test_tracked_private_key_is_critical_and_fails_even_in_ci_mode(tmp_path):
    root = _git_repo(tmp_path, {"README.md": "x", "deploy/id.pem": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n"})
    res = audit.run_audit(root, online=False)
    assert "T0.1" in res["critical"]
    assert audit.main(["--root", str(root), "--critical-only"]) == 1


def test_secret_pattern_inside_ordinary_file_is_critical(tmp_path):
    root = _git_repo(tmp_path, {"README.md": "x", "cfg.txt": "token = ghp_" + "a" * 36 + "\n"})
    assert "T0.1" in audit.run_audit(root, online=False)["critical"]


def test_unpinned_action_and_missing_permissions_lower_t3_4(tmp_path):
    wf = "name: x\non: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"
    root = _git_repo(tmp_path, {"README.md": "x", ".github/workflows/x.yml": wf})
    item = next(i for i in audit.run_audit(root, online=False)["items"] if i["ident"] == "T3.4")
    assert item["score"] < 3 and any("actions/checkout@v4" in e for e in item["evidence"])


def test_pipe_to_shell_install_is_flagged(tmp_path):
    wf = "permissions:\n  contents: read\njobs:\n  a:\n    steps:\n      - run: curl -LsSf https://x.example/i.sh | sh\n"
    root = _git_repo(tmp_path, {"README.md": "x", ".github/workflows/x.yml": wf})
    item = next(i for i in audit.run_audit(root, online=False)["items"] if i["ident"] == "T3.4")
    assert item["score"] < 3


def test_online_only_items_are_credited_zero_offline(tmp_path):
    root = _git_repo(tmp_path, {"README.md": "x"})
    item = next(i for i in audit.run_audit(root, online=False)["items"] if i["ident"] == "T1.6")
    assert item["score"] == 0 and item["verified"] is False


def test_presence_of_empty_files_does_not_earn_points(tmp_path):
    root = _git_repo(tmp_path, {n: "" for n in ("README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "LICENSE")})
    items = {i["ident"]: i for i in audit.run_audit(root, online=False)["items"]}
    assert items["T1.1"]["score"] <= 1 and items["T0.4"]["score"] <= 1
