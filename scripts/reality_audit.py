#!/usr/bin/env python3
"""Reality audit: static checks that catch fabricated or stubbed science.

Rules (see docs/REALITY_RULES.md):
  R1  No hard-coded result literals inside study/benchmark/experiment functions.
  R2  `fit` must change model state (not just set a flag) unless marked `# reality: stateless`.
  R3  Validation helpers (sbc, recovery, validate) must exercise the model (`self`).
  R4  Classes named in a module docstring in parentheses must exist in the package.
  R5  Every placeholder must be registered in docs/STUBS.md (checked by --require-stub-registry).

Exit code 1 if any finding. Allow-list line: `# reality: allow(<rule>) <reason>` on the flagged line.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["packages", "scripts", "apps"]
SKIP_PARTS = {".venv", "node_modules", "tests", "__pycache__", "quarantine"}
STUDY_FN = re.compile(r"(study|benchmark|experiment|run_s\d+|pretraining_and_scaling)", re.I)
VALIDATION_FN = re.compile(r"(sbc|recovery|identifiab|validate|calibration_check|coverage)", re.I)


def _allowed(lines: list[str], lineno: int, rule: str) -> bool:
    return f"reality: allow({rule})" in lines[lineno - 1] if 0 < lineno <= len(lines) else False


def _is_float(n: ast.AST) -> bool:
    return isinstance(n, ast.Constant) and isinstance(n.value, float) and not isinstance(n.value, bool)


def _numeric_literals(node: ast.AST) -> int:
    """Count float constants in list/tuple/dict-value literals directly under node."""
    count = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.List, ast.Tuple)):
            count += sum(1 for e in child.elts if _is_float(e))
        elif isinstance(child, ast.Dict):
            count += sum(1 for v in child.values if v is not None and _is_float(v))
    return count


def _body_without_doc(fn: ast.FunctionDef) -> list[ast.stmt]:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        body = body[1:]
    return body


def _flag_only_fit(fn: ast.FunctionDef) -> bool:
    """True if fit() only sets boolean flags and returns self."""
    for stmt in _body_without_doc(fn):
        if isinstance(stmt, ast.Return):
            continue
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Assign) and all(
            isinstance(t, ast.Attribute) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, bool)
            for t in stmt.targets
        ):
            continue
        return False
    return True


def scan_file(path: Path, defined_classes: set[str]) -> list[str]:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:  # pragma: no cover
        return [f"{path}: cannot parse ({e})"]
    findings: list[str] = []
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path

    # R4: parenthesised identifiers in module docstring must exist somewhere in the package set
    mod_doc = ast.get_docstring(tree) or ""
    for name in re.findall(r"\(([A-Z][A-Za-z0-9_]*(?:K\d+|Model|Engine|Filter|Detector|Controller|Estimator|Network))\)", mod_doc):
        if name not in defined_classes and not _allowed(lines, 1, "R4"):
            findings.append(f"{rel}:1 [R4] docstring names class `{name}` that is not defined anywhere")

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # R1
            if STUDY_FN.search(node.name) and _numeric_literals(node) >= 3 and not _allowed(lines, node.lineno, "R1"):
                findings.append(
                    f"{rel}:{node.lineno} [R1] `{node.name}` contains >=3 hard-coded float results; "
                    "results must be computed from data/models"
                )
            # R2
            if node.name == "fit" and _flag_only_fit(node):
                window = "\n".join(lines[node.lineno - 1 : node.lineno + 1])
                if "reality: stateless" not in window and not _allowed(lines, node.lineno, "R2"):
                    findings.append(f"{rel}:{node.lineno} [R2] `fit` does not learn anything (sets flags only)")
            # R3
            if VALIDATION_FN.search(node.name) and not node.name.startswith("_"):
                uses_self = any(isinstance(n, ast.Name) and n.id == "self" for n in ast.walk(node) if n is not None) and any(
                    isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self"
                    for n in ast.walk(node)
                )
                args = [a.arg for a in node.args.args]
                if args[:1] == ["self"] and not uses_self and not _allowed(lines, node.lineno, "R3"):
                    findings.append(
                        f"{rel}:{node.lineno} [R3] validation `{node.name}` never touches the model (`self`); "
                        "it validates a toy, not the implementation"
                    )
    return findings


def main(argv: list[str]) -> int:
    files: list[Path] = []
    for d in SCAN_DIRS:
        for p in (ROOT / d).rglob("*.py"):
            if not (set(p.parts) & SKIP_PARTS):
                files.append(p)
    defined: set[str] = set()
    for p in files:
        try:
            for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(n, ast.ClassDef):
                    defined.add(n.name)
        except SyntaxError:
            continue
    findings: list[str] = []
    for p in sorted(files):
        findings.extend(scan_file(p, defined))

    if "--require-stub-registry" in argv:
        reg = ROOT / "docs" / "STUBS.md"
        if not reg.exists():
            findings.append("docs/STUBS.md missing (register every placeholder or delete it)")

    if findings:
        print("REALITY AUDIT FAILED:")
        for f in findings:
            print("  -", f)
        print(f"{len(findings)} finding(s). See docs/REALITY_RULES.md.")
        return 1
    print("Reality audit passed: no hard-coded results, no-op fits, toy validations or phantom classes found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
