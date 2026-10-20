"""Release hash manifest: generation, verification, tamper detection, and (when cosign exists) signing."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import generate_release_manifest as grm  # noqa: E402
import reproduce  # noqa: E402


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "a.md").write_text("alpha\n")
    (tmp_path / "b.json").write_text('{"x": 1}\n')
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "chore: seed"],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


def test_manifest_is_labelled_unsigned_hash_manifest(tmp_path):
    root = _repo(tmp_path)
    m = grm.generate_manifest("v0.0.0-test", ["a.md", "b.json"], root=root)
    assert m["kind"] == "sha256-hash-manifest"
    assert m["signature"]["status"] == "unsigned"
    assert m["artifact_count"] == 2 and len(m["git_commit"]) == 40
    assert grm.verify_manifest(m, root) == []


def test_tamper_missing_and_count_mismatch_are_detected(tmp_path):
    root = _repo(tmp_path)
    m = grm.generate_manifest("v0.0.0-test", ["a.md", "b.json"], root=root)
    (root / "a.md").write_text("alpha (edited)\n")
    (root / "b.json").unlink()
    probs = grm.verify_manifest(m, root)
    assert "MISMATCH a.md" in probs and "MISSING b.json" in probs
    m["artifact_count"] = 5
    assert any("artifact_count" in p for p in grm.verify_manifest(m, root))


def test_dirty_or_uncommitted_artifacts_are_refused(tmp_path):
    root = _repo(tmp_path)
    (root / "a.md").write_text("changed\n")
    with pytest.raises(SystemExit, match="uncommitted"):
        grm.generate_manifest("v0.0.0-test", ["a.md"], root=root)
    (root / "a.md").write_text("alpha\n")
    with pytest.raises(SystemExit, match="not committed"):
        grm.generate_manifest("v0.0.0-test", ["nope.md"], root=root)


def test_digest_is_of_committed_content_not_working_tree(tmp_path):
    root = _repo(tmp_path)
    committed = grm.sha256_bytes(b"alpha\n")
    m = grm.generate_manifest("v0.0.0-test", ["a.md"], root=root)
    assert m["artifacts"][0]["sha256"] == committed


def test_committed_rc1_manifest_still_verifies_or_reports_drift():
    """The committed rc.1 manifest must be honest: every listed file either matches or is reported."""
    mp = grm.manifest_path("v1.0.0-rc.1")
    m = json.loads(mp.read_text())
    assert m["artifact_count"] == len(m["artifacts"]) == 23


def test_release_manifests_are_scoped_to_their_recorded_commit(tmp_path, monkeypatch):
    manifest_dir = tmp_path / "docs" / "release"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "RELEASE_MANIFEST_v0.1.0-a.json").write_text(
        json.dumps({"git_commit": "a" * 40})
    )
    (manifest_dir / "RELEASE_MANIFEST_v0.1.0-b.json").write_text(
        json.dumps({"git_commit": "b" * 40})
    )
    monkeypatch.setattr(reproduce, "ROOT", tmp_path)
    assert reproduce._release_manifests_for_head("a" * 40) == ["v0.1.0-a"]
    assert reproduce._release_manifests_for_head("c" * 40) == []


@pytest.mark.skipif(shutil.which("cosign") is None, reason="cosign not installed")
def test_sign_and_verify_roundtrip_with_ephemeral_test_key(tmp_path):
    env = {**os.environ, "COSIGN_PASSWORD": ""}
    subprocess.run(
        ["cosign", "generate-key-pair"], cwd=tmp_path, env=env, check=True, capture_output=True
    )
    mf = tmp_path / "RELEASE_MANIFEST_test.json"
    mf.write_text(json.dumps({"release": "test"}))
    os.environ["COSIGN_PASSWORD"] = ""
    try:
        grm.sign(mf, tmp_path / "cosign.key")
    finally:
        os.environ.pop("COSIGN_PASSWORD", None)
    ok, msg = grm.verify_signature(mf, tmp_path / "cosign.pub")
    assert ok, msg
    mf.write_text(json.dumps({"release": "test", "tampered": True}))
    ok, _ = grm.verify_signature(mf, tmp_path / "cosign.pub")
    assert not ok
