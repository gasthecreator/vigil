#!/usr/bin/env python3
"""Write (or check) packages/vigil-ml/vigil_ml/registry/model_registry.json.

The registry says, for each exportable research model: the module, the export formats, the tests that prove export
parity, the study that evaluated it (with the sha256 of its committed result file) and its status. It contains no
metric values; numbers live only in the study's result file. `--check` fails if the file is stale, a cited test
function does not exist, or a cited result file changed.

    uv run python scripts/build_model_registry.py [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packages" / "vigil-ml" / "vigil_ml" / "registry" / "model_registry.json"

ENTRIES = [
    {
        "id": "K5",
        "name": "Laboratory harmonisation (REML partial pooling of laboratory offsets)",
        "module": "packages/vigil-ml/vigil_ml/k5.py",
        "maturity": "L0",
        "status": "research; claim not earned (pre-registered criterion failed, ADR-0024); not wired to any pipeline",
        "data": "synthetic only",
        "formats": {"safetensors": "format vigil-k5-v1, JSON metadata, no pickle", "onnx": "Gather, Exp, Div graph"},
        "parity_tests": [
            "packages/vigil-ml/tests/test_k5.py::test_safetensors_and_onnx_parity",
            "packages/vigil-ml/tests/test_k5.py::test_unseen_laboratory_is_left_unchanged",
        ],
        "study": {
            "prereg": "experiments/EXP-K5-001/PREREG.md",
            "result_file": "experiments/EXP-K5-001/results.json",
            "conclusion": "experiments/EXP-K5-001/CONCLUSION.md",
        },
        "model_card": "docs/model_cards/MODEL-CARD-K5.md",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    out = []
    for e in ENTRIES:
        e = json.loads(json.dumps(e))
        for key in ("result_file",):
            p = ROOT / e["study"][key]
            e["study"]["result_sha256"] = sha256(p)
        out.append(e)
    return {"schema": "vigil-model-registry-v1", "models": out}


def problems(reg: dict) -> list[str]:
    bad = []
    for e in reg["models"]:
        for t in e["parity_tests"]:
            f, _, name = t.partition("::")
            fp = ROOT / f
            if not fp.exists() or not re.search(rf"^def {re.escape(name)}\(", fp.read_text(encoding="utf-8"), re.M):
                bad.append(f"{e['id']}: cited test not found: {t}")
        for k in ("module", "model_card"):
            if not (ROOT / e[k]).exists():
                bad.append(f"{e['id']}: missing {k} {e[k]}")
        for k, v in e["study"].items():
            if k.endswith("_sha256"):
                continue
            if not (ROOT / v).exists():
                bad.append(f"{e['id']}: missing study file {v}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    reg = build()
    bad = problems(reg)
    text = json.dumps(reg, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            bad.append("registry file is stale; run scripts/build_model_registry.py")
        for b in bad:
            print("FAIL:", b)
        return 1 if bad else 0
    if bad:
        for b in bad:
            print("FAIL:", b)
        return 1
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
