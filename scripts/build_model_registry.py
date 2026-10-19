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
        "id": "M12",
        "name": "In-process FederatedAveraging and DP-SGD (research MLP)",
        "module": "packages/vigil-ml/vigil_ml/m12.py",
        "maturity": "L0",
        "status": "research; simulation claim only (ADR-0027); not wired to any pipeline",
        "data": "synthetic only",
        "formats": {"arrays": "in-process float32 weight lists; no pickle"},
        "parity_tests": [
            "packages/vigil-ml/tests/test_m12.py::test_fedavg_identity_n_weighted_mean",
            "packages/vigil-ml/tests/test_m12.py::test_accountant_recovers_abadi_example",
            "packages/vigil-ml/tests/test_m12.py::test_no_raw_data_egress_or_pickle",
        ],
        "study": {
            "prereg": "experiments/EXP-M12-001/PREREG.md",
            "result_file": "experiments/EXP-M12-001/results.json",
            "conclusion": "experiments/EXP-M12-001/CONCLUSION.md",
        },
        "model_card": "docs/model_cards/MODEL-CARD-M12.md",
    },
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
    {
        "id": "K4",
        "name": "Deep irregular-time risk models (GRU-D, GRU-ODE-Bayes, Neural CDE, continuous-time transformer, GRUwE, state-space) with masked-analyte pre-training code",
        "module": "packages/vigil-ml/vigil_ml/k4.py",
        "maturity": "L0",
        "status": "research; claim not earned (pre-registered kill rules H1, H2 fired and scale does not help, ADR-0025); no pre-trained checkpoint exported or registered; not wired to any pipeline or ensemble",
        "data": "synthetic only",
        "formats": {"safetensors": "format vigil-k4-v1, JSON metadata, no pickle", "onnx": "opset 17, dynamic batch, probabilities"},
        "parity_tests": [
            "packages/vigil-ml/tests/test_k4.py::test_safetensors_round_trip_and_onnx_parity",
            "packages/vigil-ml/tests/test_k4.py::test_causality_later_visits_never_change_earlier_outputs",
            "packages/vigil-ml/tests/test_k4.py::test_each_family_learns_a_planted_signal_and_not_shuffled_labels",
        ],
        "study": {
            "prereg": "experiments/EXP-K4-001/PREREG.md",
            "result_file": "experiments/EXP-K4-001/results.json",
            "conclusion": "experiments/EXP-K4-001/CONCLUSION.md",
        },
        "model_card": "docs/model_cards/MODEL-CARD-K4.md",
    },
    {
        "id": "K6",
        "name": "Active sensing planner (finite-horizon cost-of-delay, calibrated multi-horizon hazard)",
        "module": "packages/vigil-ml/vigil_ml/k6.py",
        "maturity": "L0",
        "status": "research; simulation claim only (H1 and H2 met on synthetic data, H3 not met, ADR-0026); not wired to any pipeline",
        "data": "synthetic only",
        "formats": {"xgboost_json": "one booster per horizon plus isotonic knots; no pickle"},
        "parity_tests": [
            "packages/vigil-ml/tests/test_k6.py::test_hazard_model_round_trips_through_text_with_identical_output_and_no_binary_object_format",
            "packages/vigil-ml/tests/test_k6.py::test_policy_code_never_names_a_truth_column",
        ],
        "study": {
            "prereg": "experiments/EXP-K6-001/PREREG.md",
            "result_file": "experiments/EXP-K6-001/results.json",
            "conclusion": "experiments/EXP-K6-001/CONCLUSION.md",
        },
        "model_card": "docs/model_cards/MODEL-CARD-K6.md",
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
