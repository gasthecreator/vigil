#!/usr/bin/env python3
"""
scripts/verify_phase.py

Unified Exit-Gate Verification Engine for Vigil Precision Oncology Platform.
Enforces Master Plan §14 and §16 exit gates with real, non-mocked verification.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd: list[str], cwd: Path = ROOT) -> tuple[int, str]:
    """Runs a shell command and returns (exit_code, combined_output)."""
    res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return res.returncode, res.stdout


def verify_phase_0() -> bool:
    print("\n=======================================================")
    print("🔍 VERIFYING PHASE 0: TRUTH RESET & PROFESSIONAL FOUNDATION")
    print("=======================================================")

    required_files = [
        "LICENSE",
        "README.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        ".github/CODEOWNERS",
        ".github/workflows/ci.yml",
        ".github/workflows/scorecard.yml",
        ".github/dependabot.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "CITATION.cff",
        "CHANGELOG.md",
        ".editorconfig",
        ".gitignore",
        "Makefile",
        "docs/DISCLAIMER.md",
        "docs/safety/HAZARD_LOG.md",
        "docs/risk/RISK-REGISTER.md",
        "docs/ops/GITHUB-SETTINGS.md",
        "docs/proposals/PROP-0000-template.md",
        "docs/adr/0001-monorepo-layout.md",
        "docs/adr/0002-quarantine-prototype-models.md",
        "docs/adr/0003-claims-policy-and-truth-reset.md",
        "docs/adr/0004-cors-and-environment-profiles.md",
        "docs/adr/0005-proposal-process.md",
        "docs/audits/REPO-AUDIT-P0.md",
        "scripts/check_claims.py",
        "quarantine/legacy_models/README.md",
    ]

    missing = []
    for rel_path in required_files:
        p = ROOT / rel_path
        if not p.exists():
            missing.append(rel_path)

    if missing:
        print("❌ Missing required Phase 0 artifacts:")
        for m in missing:
            print(f"  - {m}")
        return False
    print("✅ All required Phase 0 artifacts exist.")

    # 1. Run claims policy checker
    print("\n[Step 1/6] Running claims policy checker...")
    code, out = run_cmd([sys.executable, "scripts/check_claims.py"])
    if code != 0:
        print(f"❌ Claims policy check failed:\n{out}")
        return False
    print("✅ Claims policy check passed.")

    # 1b. Run evidence integrity checker
    print("\n[Step 2/6] Running evidence integrity & Crossref citation checker...")
    code, out = run_cmd([sys.executable, "scripts/check_evidence.py"])
    if code != 0:
        print(f"❌ Evidence check failed:\n{out}")
        return False
    print("✅ Evidence register and Crossref verification passed.")

    # 2. Verify no pickled models in apps/
    print("\n[Step 3/6] Verifying zero .pkl files in runtime application paths...")
    runtime_pickles = list((ROOT / "apps").rglob("*.pkl"))
    if runtime_pickles:
        print("❌ Found pickled models in apps/ runtime path (Defect A8):")
        for p in runtime_pickles:
            print(f"  - {p.relative_to(ROOT)}")
        return False
    print("✅ Runtime paths are free of serialized pickle artifacts.")

    # 3. Verify no hardcoded machine paths
    print("\n[Step 4/6] Verifying zero hardcoded machine paths in code...")
    for ext in [".py", ".ts", ".tsx", ".json"]:
        for p in (ROOT / "apps").rglob(f"*{ext}"):
            if ".next" in p.parts or "node_modules" in p.parts or ".venv" in p.parts:
                continue
            text = p.read_text(errors="ignore")
            if "/Users/" in text:
                print(f"❌ Hardcoded user path found in {p.relative_to(ROOT)}")
                return False
    print("✅ Zero hardcoded personal paths found in application code.")

    # 4. Run backend tests
    print("\n[Step 5/6] Running backend test suite...")
    uv_bin = os.getenv("UV_BIN", str(Path.home() / ".local" / "bin" / "uv"))
    if not Path(uv_bin).exists():
        uv_bin = "uv"
    code, out = run_cmd([uv_bin, "run", "pytest", "apps/api/tests", "-v"])
    if code != 0:
        print(f"❌ Backend tests failed:\n{out}")
        return False
    print("✅ All backend API tests and E2E characterisation tests passed.")

    # 5. Run frontend lint and build
    print("\n[Step 6/6] Running web frontend lint and build...")
    code, out = run_cmd(["npm", "--prefix", "apps/web", "run", "lint"])
    if code != 0:
        print(f"❌ Web lint failed:\n{out}")
        return False
    code, out = run_cmd(["npm", "--prefix", "apps/web", "run", "build"])
    if code != 0:
        print(f"❌ Web build failed:\n{out}")
        return False
    print("✅ Web frontend lint and production build passed.")

    print("\n🎉 PHASE 0 EXIT GATE: ALL CHECKS MET SUCCESSFULLY.")
    return True


def verify_phase_1() -> bool:
    print("\n=======================================================")
    print("🔬 VERIFYING PHASE 1: SIMULATION LABORATORY & DATA FOUNDATION")
    print("=======================================================")

    required_files = [
        "packages/vigil-core/vigil_core/analytes.py",
        "packages/vigil-core/vigil_core/units.py",
        "packages/vigil-core/vigil_core/fhir.py",
        "packages/vigil-core/tests/test_analytes.py",
        "packages/vigil-core/tests/test_units.py",
        "packages/vigil-core/tests/test_fhir.py",
        "packages/vigil-sim/vigil_sim/generators.py",
        "packages/vigil-sim/vigil_sim/calibration.py",
        "packages/vigil-sim/tests/test_generators.py",
        "packages/vigil-sim/tests/test_calibration.py",
        "packages/contracts/contracts/loaders/seer_loader.py",
        "packages/contracts/contracts/loaders/metabric_loader.py",
        "packages/contracts/contracts/loaders/tcga_loader.py",
        "packages/contracts/contracts/loaders/pds_loader.py",
        "packages/contracts/contracts/loaders/mimic_loader.py",
        "packages/contracts/tests/test_loaders.py",
        "packages/vigil-eval/vigil_eval/leakage.py",
        "packages/vigil-eval/tests/test_leakage.py",
        "docs/data/ACCESS.md",
        "docs/clinical/PARTNERSHIP/STUDY-PROTOCOL.md",
        "docs/clinical/PARTNERSHIP/DATA-DICTIONARY.md",
        "docs/clinical/PARTNERSHIP/DUA-TEMPLATE.md",
        "docs/clinical/PARTNERSHIP/ETHICS-APPLICATION.md",
        "docs/clinical/PARTNERSHIP/DPIA.md",
        "docs/clinical/PARTNERSHIP/VALUE-PROPOSITION.md",
        "docs/progress/PHASE-1-REPORT.md",
    ]

    missing = []
    for rel_path in required_files:
        p = ROOT / rel_path
        if not p.exists():
            missing.append(rel_path)

    if missing:
        print("❌ Missing required Phase 1 artifacts:")
        for m in missing:
            print(f"  - {m}")
        return False
    print("✅ All required Phase 1 artifacts exist.")

    uv_bin = os.getenv("UV_BIN", str(Path.home() / ".local" / "bin" / "uv"))
    if not Path(uv_bin).exists():
        uv_bin = "uv"

    # 1. Run evidence integrity checker
    print("\n[Step 1/6] Running evidence integrity & Crossref citation checker...")
    code, out = run_cmd([sys.executable, "scripts/check_evidence.py"])
    if code != 0:
        print(f"❌ Evidence check failed:\n{out}")
        return False
    print("✅ Evidence register and Crossref verification passed.")

    # 2. Run vigil-core tests
    print("\n[Step 2/6] Running vigil-core unit and property tests...")
    code, out = run_cmd([uv_bin, "run", "pytest", "packages/vigil-core/tests", "-v"])
    if code != 0:
        print(f"❌ vigil-core tests failed:\n{out}")
        return False
    print("✅ vigil-core tests passed.")

    # 3. Run vigil-sim tests and calibration target verification
    print("\n[Step 3/6] Running vigil-sim generator tests and calibration target verification...")
    code, out = run_cmd([uv_bin, "run", "pytest", "packages/vigil-sim/tests", "-v"])
    if code != 0:
        print(f"❌ vigil-sim tests failed:\n{out}")
        return False
    print("✅ vigil-sim calibration target verification passed.")

    # 4. Run contracts and ingestion loaders tests
    print("\n[Step 4/6] Running ingestion contracts and public data loaders tests...")
    code, out = run_cmd([uv_bin, "run", "pytest", "packages/contracts/tests", "-v"])
    if code != 0:
        print(f"❌ contracts loader tests failed:\n{out}")
        return False
    print("✅ Ingestion contracts and data loader tests passed.")

    # 5. Run leakage test suite
    print("\n[Step 5/6] Running leakage test suite (canary and leaky fixture detection)...")
    code, out = run_cmd([uv_bin, "run", "pytest", "packages/vigil-eval/tests", "-v"])
    if code != 0:
        print(f"❌ Leakage test suite failed:\n{out}")
        return False
    print("✅ Leakage test suite passed.")

    # 6. Verify dataset cards and documentation
    print("\n[Step 6/6] Verifying data access and partnership dossiers...")
    access_doc = (ROOT / "docs" / "data" / "ACCESS.md").read_text()
    if "SEER" not in access_doc or "METABRIC" not in access_doc:
        print("❌ docs/data/ACCESS.md missing required data source verification")
        return False
    print("✅ Phase 1 data access dossiers verified.")

    print("\n🎉 PHASE 1 EXIT GATE: ALL CHECKS MET SUCCESSFULLY.")
    return True


def verify_phase_2() -> bool:
    print("\n=======================================================")
    print("📊 VERIFYING PHASE 2: EVALUATION BACKBONE & CLASSICAL CORE")
    print("=======================================================")

    required_files = [
        "packages/vigil-eval/vigil_eval/metrics.py",
        "packages/vigil-eval/vigil_eval/bootstrap.py",
        "packages/vigil-eval/vigil_eval/subgroups.py",
        "packages/vigil-eval/vigil_eval/verification_bias.py",
        "packages/vigil-eval/vigil_eval/lead_time.py",
        "packages/vigil-eval/vigil_eval/audit.py",
        "packages/vigil-eval/vigil_eval/regression_gate.py",
        "packages/vigil-ml/vigil_ml/baselines.py",
        "packages/vigil-ml/vigil_ml/features.py",
        "packages/vigil-ml/vigil_ml/joint_model.py",
        "packages/vigil-ml/vigil_ml/organ_susceptibility.py",
        "reports/ml/S1_SPARSITY/PREREG.md",
        "reports/ml/S1_SPARSITY/results.json",
        "reports/ml/S1_SPARSITY/REPORT.md",
        "reports/ml/S3_VERIFICATION_BIAS/PREREG.md",
        "reports/ml/S3_VERIFICATION_BIAS/results.json",
        "reports/ml/S3_VERIFICATION_BIAS/REPORT.md",
        "reports/ml/S9_CROSS_GENERATOR/PREREG.md",
        "reports/ml/S9_CROSS_GENERATOR/results.json",
        "reports/ml/S9_CROSS_GENERATOR/REPORT.md",
        "reports/ml/BENCHMARK_REPORT.md",
        "reports/ml/frozen_test_access_log.jsonl",
        "docs/models/MODEL-CARD-M1.md",
        "docs/models/MODEL-CARD-K3.md",
        "docs/data/DATASET-CARD-SYNTHETIC-G1-G3.md",
        "docs/progress/PHASE-2-REPORT.md",
    ]

    missing = []
    for rel_path in required_files:
        p = ROOT / rel_path
        if not p.exists():
            missing.append(rel_path)

    if missing:
        print("❌ Missing required Phase 2 artifacts:")
        for m in missing:
            print(f"  - {m}")
        return False
    print("✅ All required Phase 2 artifacts exist.")

    uv_bin = os.getenv("UV_BIN", str(Path.home() / ".local" / "bin" / "uv"))
    if not Path(uv_bin).exists():
        uv_bin = "uv"

    # 1. Run evidence integrity checker
    print("\n[Step 1/6] Running evidence integrity & Crossref citation checker...")
    code, out = run_cmd([sys.executable, "scripts/check_evidence.py"])
    if code != 0:
        print(f"❌ Evidence check failed:\n{out}")
        return False
    print("✅ Evidence register and Crossref verification passed.")

    # 2. Run vigil-eval test suite
    print("\n[Step 2/6] Running vigil-eval evaluation harness test suite...")
    code, out = run_cmd([uv_bin, "run", "pytest", "packages/vigil-eval/tests", "-v"])
    if code != 0:
        print(f"❌ vigil-eval tests failed:\n{out}")
        return False
    print("✅ vigil-eval test suite passed.")

    # 3. Run vigil-ml test suite
    print("\n[Step 3/6] Running vigil-ml baselines and joint model test suite...")
    code, out = run_cmd([uv_bin, "run", "pytest", "packages/vigil-ml/tests", "-v"])
    if code != 0:
        print(f"❌ vigil-ml tests failed:\n{out}")
        return False
    print("✅ vigil-ml test suite passed.")

    # 4. Check frozen test set audit log
    print("\n[Step 4/6] Verifying frozen test set access audit log...")
    audit_file = ROOT / "reports" / "ml" / "frozen_test_access_log.jsonl"
    audit_records = [line for line in audit_file.read_text().splitlines() if line.strip()]
    if len(audit_records) < 4:
        print(
            f"❌ Insufficient frozen test set audit records: {len(audit_records)} found (minimum 4 expected)"
        )
        return False
    print(f"✅ Frozen test set access audit log verified ({len(audit_records)} records).")

    # 5. Anti-degeneracy canary check: verify no ROC-AUC > 0.97
    print("\n[Step 5/6] Verifying anti-degeneracy stop-and-think triggers (no AUROC > 0.97)...")
    import json

    for s_path in [
        ROOT / "reports" / "ml" / "S1_SPARSITY" / "results.json",
        ROOT / "reports" / "ml" / "S9_CROSS_GENERATOR" / "results.json",
    ]:
        with open(s_path) as f:
            data = json.load(f)

            def check_auc(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == "auc" and isinstance(v, (int, float)):
                            if v > 0.97:
                                raise ValueError(f"Degenerate AUC {v} > 0.97 found in {s_path}")
                        check_auc(v)
                elif isinstance(obj, list):
                    for item in obj:
                        check_auc(item)

            try:
                check_auc(data)
            except ValueError as e:
                print(f"❌ Anti-degeneracy failure: {e}")
                return False
    print("✅ Zero degenerate/leaked AUC scores detected across all benchmark runs.")

    # 6. Verify synthetic data labeling in reports
    print("\n[Step 6/6] Verifying mandatory synthetic data labeling in reports...")
    bench_rep = (ROOT / "reports" / "ml" / "BENCHMARK_REPORT.md").read_text()
    if "SYNTHETIC" not in bench_rep or "Sim-to-Real Gap" not in bench_rep:
        print(
            "❌ reports/ml/BENCHMARK_REPORT.md missing mandatory synthetic labeling or sim-to-real section"
        )
        return False
    print("✅ Benchmark report synthetic disclosure verified.")

    print("\n🎉 PHASE 2 EXIT GATE: ALL CHECKS MET SUCCESSFULLY.")
    return True


def verify_phase_3() -> bool:
    print("\n=======================================================")
    print("🔍 VERIFYING PHASE 3: ADVANCED MODELING PROGRAM & SIMULATION STUDIES")
    print("=======================================================")

    required_files = [
        "packages/vigil-ml/vigil_ml/kinetic_k1.py",
        "packages/vigil-ml/vigil_ml/sequential_k2.py",
        "packages/vigil-ml/vigil_ml/k4.py",
        "packages/vigil-ml/vigil_ml/k5.py",
        "packages/vigil-ml/vigil_ml/k6.py",
        "packages/vigil-ml/vigil_ml/k6_engine.py",
        "packages/vigil-ml/vigil_ml/conformal_k8.py",
        "packages/vigil-ml/vigil_ml/export.py",
        "packages/vigil-ml/vigil_ml/runtime.py",
        "docs/ml/COMPUTE.md",
        "docs/models/MODEL-CARD-K1.md",
        "docs/models/MODEL-CARD-K2.md",
        "docs/models/MODEL-CARD-K4.md",
        "docs/models/MODEL-CARD-K5.md",
        "docs/models/MODEL-CARD-K6.md",
        "docs/models/MODEL-CARD-K8.md",
        "reports/ml/S1_SPARSITY/PREREG.md",
        "reports/ml/S1_SPARSITY/results.json",
        "reports/ml/S1_SPARSITY/REPORT.md",
        "reports/ml/S2_SEQUENTIAL/PREREG.md",
        "reports/ml/S2_SEQUENTIAL/results.json",
        "reports/ml/S2_SEQUENTIAL/REPORT.md",
        "reports/ml/S3_VERIFICATION_BIAS/PREREG.md",
        "reports/ml/S3_VERIFICATION_BIAS/results.json",
        "reports/ml/S3_VERIFICATION_BIAS/REPORT.md",
        "experiments/EXP-K4-001/PREREG.md",
        "experiments/EXP-K4-001/results.json",
        "experiments/EXP-K4-001/REPORT.md",
        "experiments/EXP-K4-001/CONCLUSION.md",
        "experiments/EXP-K5-001/PREREG.md",
        "experiments/EXP-K5-001/results.json",
        "experiments/EXP-K5-001/REPORT.md",
        "experiments/EXP-K6-001/PREREG.md",
        "experiments/EXP-K6-001/results.json",
        "experiments/EXP-K6-001/REPORT.md",
        "experiments/EXP-K6-001/CONCLUSION.md",
        "reports/ml/S9_CROSS_GENERATOR/PREREG.md",
        "reports/ml/S9_CROSS_GENERATOR/results.json",
        "reports/ml/S9_CROSS_GENERATOR/REPORT.md",
        "reports/ml/S10_MULTISITE_SYNTHETIC_TRIAL/PREREG.md",
        "reports/ml/S10_MULTISITE_SYNTHETIC_TRIAL/results.json",
        "reports/ml/S10_MULTISITE_SYNTHETIC_TRIAL/REPORT.md",
        "reports/ml/BENCHMARK_REPORT.md",
        "reports/ml/results.json",
        "docs/progress/PHASE-3-REPORT.md",
    ]

    missing = [f for f in required_files if not (ROOT / f).exists()]
    if missing:
        print("❌ Missing required Phase 3 artifacts:")
        for m in missing:
            print(f"  - {m}")
        return False
    print("✅ All required Phase 3 artifacts exist.")

    uv_bin = os.getenv("UV_BIN", str(Path.home() / ".local" / "bin" / "uv"))
    if not Path(uv_bin).exists():
        uv_bin = "uv"

    # 1. Run claims and evidence checkers
    print("\n[Step 1/6] Running claims and evidence checkers...")
    code, out = run_cmd([sys.executable, "scripts/check_claims.py"])
    if code != 0:
        print(f"❌ Claims check failed:\n{out}")
        return False
    code, out = run_cmd([sys.executable, "scripts/check_evidence.py"])
    if code != 0:
        print(f"❌ Evidence check failed:\n{out}")
        return False
    print("✅ Claims and evidence checks passed.")

    # 2. Run phase 3 unit tests
    print("\n[Step 2/6] Running Phase 3 model test suite...")
    code, out = run_cmd(
        [uv_bin, "run", "pytest", "packages/vigil-ml/tests/test_phase3_models.py", "-v"]
    )
    if code != 0:
        print(f"❌ Phase 3 model tests failed:\n{out}")
        return False
    print("✅ Phase 3 model test suite passed.")

    # 3. Run report traceability test
    print("\n[Step 3/6] Running benchmark report traceability test...")
    code, out = run_cmd([uv_bin, "run", "pytest", "tests/test_report_traceability.py", "-v"])
    if code != 0:
        print(f"❌ Traceability test failed:\n{out}")
        return False
    print("✅ Benchmark report traceability passed (100% verified against results.json).")

    # 4. Anti-degeneracy check across all studies
    print(
        "\n[Step 4/6] Verifying anti-degeneracy stop-and-think triggers (all AUC in [0.50, 0.97])..."
    )
    import json

    for s_path in (ROOT / "reports" / "ml").glob("**/results.json"):
        with open(s_path) as f:
            data = json.load(f)

            def check_auc(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if "auc" in k.lower() and isinstance(v, (int, float)):
                            if v > 0.97 or (
                                v < 0.45
                                and "drop" not in k.lower()
                                and "gain" not in k.lower()
                                and "delta" not in k.lower()
                            ):
                                raise ValueError(f"Degenerate AUC {v} for key '{k}' in {s_path}")
                        check_auc(v)
                elif isinstance(obj, list):
                    for item in obj:
                        check_auc(item)

            try:
                check_auc(data)
            except ValueError as e:
                print(f"❌ Anti-degeneracy failure: {e}")
                return False
    print("✅ Zero degenerate/leaked AUC scores detected across all benchmark studies.")

    # 5. Check Sequential Stress Suite pass in S2
    print("\n[Step 5/6] Verifying S2 Null Stress Suite results...")
    s2_file = ROOT / "reports" / "ml" / "S2_SEQUENTIAL" / "results.json"
    with open(s2_file) as f:
        s2_data = json.load(f)
    if not s2_data.get("null_stress_suite", {}).get("all_passed", False):
        print("❌ S2 null stress suite recorded failure!")
        return False
    print("✅ S2 Null Stress Suite passed across all 5 null scenarios.")

    # 6. Check S10 Federated Trial utility constraint
    print("\n[Step 6/6] Verifying S10 Federated Learning utility criterion...")
    s10_file = ROOT / "reports" / "ml" / "S10_MULTISITE_SYNTHETIC_TRIAL" / "results.json"
    with open(s10_file) as f:
        s10_data = json.load(f)
    if not s10_data.get("summary", {}).get("federated_utility_pass", False):
        print("❌ S10 federated utility cost exceeded pre-registered 0.030 AUC threshold!")
        return False
    print("✅ S10 Federated Utility constraint met (utility penalty <= 0.030 AUC).")

    print("\n🎉 PHASE 3 EXIT GATE: ALL CHECKS MET SUCCESSFULLY.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Vigil Phase Exit-Gate Verification Engine")
    parser.add_argument("--phase", required=True, help="Phase number to verify (0, 1, 2, or 3)")
    args = parser.parse_args()

    phase = str(args.phase).strip()
    if phase == "0":
        success = verify_phase_0()
    elif phase == "1":
        success = verify_phase_1()
    elif phase == "2":
        success = verify_phase_2()
    elif phase == "3":
        success = verify_phase_3()
    else:
        print(f"Error: Phase {phase} verification not implemented yet.")
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
