"""The clean-clone verifier must not consume one-time frozen study cohorts."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts" / "verify_study_reproducibility.py"
FROZEN_STUDY_VERIFIERS = {
    "verify_k4_study",
    "verify_k5_study",
    "verify_k6_study",
    "verify_m12_study",
    "verify_m7_cpsat_v2",
}
FROZEN_RUN_METHODS = {"replication", "run_rep", "unit_baselines"}


def test_clean_clone_verifier_does_not_replay_frozen_model_studies() -> None:
    tree = ast.parse(VERIFIER.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in FROZEN_STUDY_VERIFIERS
    }
    assert set(functions) == FROZEN_STUDY_VERIFIERS

    violations: list[str] = []
    for name, function in functions.items():
        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                method = node.func.attr if isinstance(node.func, ast.Attribute) else None
                has_frozen_seed = any(
                    isinstance(arg, ast.Constant) and arg.value == "frozen"
                    for arg in (*node.args, *(kw.value for kw in node.keywords))
                )
                if method in FROZEN_RUN_METHODS or has_frozen_seed or method == "run":
                    violations.append(f"{name}:{node.lineno} replays a frozen study path")

    assert not violations, "\n".join(violations)
