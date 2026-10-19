#!/usr/bin/env python3
"""scripts/verify_study_reproducibility.py

Automated Study Reproducibility and Anti-Fabrication Check.
Enforces Master Plan §3, §10, Reality Rule RR1, and Overseer Condition P14-A.

Re-runs fast/cheap study scripts (e.g. Study M10-V2 Missed-Signal Audit),
verifies exact deterministic reproduction of results against committed artifacts,
and verifies mathematical integrity of S8-K7 causal and M7 twin study records.
Fails CI if any committed study result is stale, drift-prone, or hand-edited.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:  # xgboost must be imported before torch on macOS (two OpenMP runtimes); harmless elsewhere
    import xgboost  # noqa: F401
except ImportError:  # pragma: no cover
    pass


def verify_m10_reproducibility() -> bool:
    print("🔬 Verifying deterministic reproduction of Study M10-V2...")
    m10_json_path = ROOT / "reports" / "ml" / "STUDY_M10_MISSED_SIGNALS.json"
    if not m10_json_path.exists():
        print(f"❌ Error: {m10_json_path} does not exist.")
        return False

    with open(m10_json_path) as f:
        committed_data = json.load(f)

    # Execute study script in-process or via subprocess
    cmd = [sys.executable, str(ROOT / "scripts" / "run_study_m10_audit.py")]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Error: run_study_m10_audit.py failed:\n{res.stderr}")
        return False

    with open(m10_json_path) as f:
        new_data = json.load(f)

    # Compare all facility results and hypotheses (excluding volatile timestamp)
    # Compare every key except the volatile timestamp. An earlier version listed key names that do not
    # exist in the report, so both sides were None and the check could never fail (overseer review, PR #71).
    match = bool(committed_data) and set(committed_data) == set(new_data)
    if not match:
        print("❌ M10 report key set changed or is empty!")
    for key in sorted((set(committed_data) | set(new_data)) - {"timestamp_utc"}):
        if committed_data.get(key) != new_data.get(key):
            print(f"❌ M10 reproducibility mismatch in section '{key}'!")
            match = False

    if match:
        print("  ✅ Study M10-V2 reproduced bit-for-bit with committed JSON.")
    return match


def verify_s8_k7_integrity() -> bool:
    print("🔬 Verifying Study S8-K7 Causal Inference result integrity...")
    s8_json_path = ROOT / "reports" / "ml" / "STUDY_S8_K7_CAUSAL.json"
    if not s8_json_path.exists():
        print(f"❌ Error: {s8_json_path} does not exist.")
        return False

    with open(s8_json_path) as f:
        data = json.load(f)

    h3 = data["hypotheses"]["H3_unmeasured_confounding_sensitivity"]
    sa = data["scenario_a_measured_confounding"]
    sb = data["scenario_b_unmeasured_confounding"]

    errors = []
    # Verify ground truth reconciliation
    if h3.get("conditional_parameter_rr") != 1.18:
        errors.append("H3 conditional_parameter_rr must equal 1.18")
    if round(sa["ground_truth_marginal_rr"], 4) != 1.1436:
        errors.append(f"Scenario A marginal RR mismatch: expected 1.1436, got {sa['ground_truth_marginal_rr']}")
    if round(h3.get("ground_truth_marginal_rr", 0), 4) != round(sb["ground_truth_marginal_rr"], 4):
        errors.append("H3 ground_truth_marginal_rr does not match scenario B marginal RR")

    # Verify calculated bias consistency
    expected_marginal_bias = round(h3["biased_aipw_rr"] - h3["ground_truth_marginal_rr"], 4)
    if round(h3.get("bias_vs_marginal_truth", 0), 4) != expected_marginal_bias:
        errors.append(f"H3 bias_vs_marginal_truth {h3.get('bias_vs_marginal_truth')} != {expected_marginal_bias}")

    expected_cond_bias = round(h3["biased_aipw_rr"] - 1.18, 4)
    if round(h3.get("bias_vs_conditional_parameter", 0), 4) != expected_cond_bias:
        errors.append(f"H3 bias_vs_conditional_parameter {h3.get('bias_vs_conditional_parameter')} != {expected_cond_bias}")

    # Verify E-value
    e_est = h3["e_value_estimate"]
    if e_est < 2.0:
        errors.append(f"H3 E-value estimate {e_est} unexpectedly low for injected confounder")

    if errors:
        print("❌ S8-K7 Integrity Verification Failed:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("  ✅ Study S8-K7 passed mathematical and ground-truth reconciliation checks.")
    return True


def verify_m7_cpsat_v2() -> bool:
    print("🔬 Verifying EXP-M7-001 (CP-SAT research track) against committed results...")
    exp = ROOT / "experiments" / "EXP-M7-001"
    # (1) Re-run the first replications of one frozen cell and compare every metric to results.json.
    cmd = [sys.executable, str(ROOT / "scripts" / "run_study_m7_cpsat_v2.py"), "--mode", "verify", "--reps", "2"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ EXP-M7-001 verify failed:\n{res.stdout}\n{res.stderr}")
        return False
    print("  " + res.stdout.strip().splitlines()[-1])
    # (2) Re-derive the all-in analysis from results.json in-process and compare with the committed file.
    sys.path.insert(0, str(ROOT / "scripts"))
    from analyze_m7_cpsat_v2_allin import analyse

    derived = analyse(json.loads((exp / "results.json").read_text()))
    committed = json.loads((exp / "ALLIN_ANALYSIS.json").read_text())
    if json.loads(json.dumps(derived, sort_keys=True)) != committed:
        print("❌ ALLIN_ANALYSIS.json does not match a fresh derivation from results.json (stale or hand-edited).")
        return False
    print("  ✅ ALLIN_ANALYSIS.json equals a fresh derivation from results.json.")
    return True


def _first_diff(a, b, tol: float = 1e-6, path: str = "") -> str | None:
    """Path of the first difference (floats compared with a relative tolerance), or None if equal."""
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return f"{path}: keys differ"
        for k in a:
            d = _first_diff(a[k], b[k], tol, f"{path}/{k}")
            if d:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: lengths differ"
        for i, (x, y) in enumerate(zip(a, b)):
            d = _first_diff(x, y, tol, f"{path}[{i}]")
            if d:
                return d
        return None
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return None if a == b else f"{path}: {a} != {b}"
        ok = abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))
        return None if ok else f"{path}: {a} != {b}"
    return None if a == b else f"{path}: {a} != {b}"


def _close(a, b, tol: float = 1e-6) -> bool:
    d = _first_diff(a, b, tol)
    if d:
        print(f"    first difference: {d}")
    return d is None


def verify_m12_study() -> bool:
    print("🔬 Verifying EXP-M12-001 (M12 FedAvg/DP-SGD) against committed results...")
    import importlib.util

    exp = ROOT / "experiments" / "EXP-M12-001"
    stored = json.loads((exp / "results.json").read_text())
    spec = importlib.util.spec_from_file_location("exp_m12_run_verify", exp / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_m12_run_verify"] = mod
    spec.loader.exec_module(mod)
    fresh = json.loads(json.dumps(mod.replication(("frozen", 0, False))))
    stored0 = json.loads(json.dumps(stored["replications"][0]))
    fresh.pop("wall_s", None)
    stored0.pop("wall_s", None)
    # Neural training floats differ across BLAS/platform builds (CI saw ECE at ~2e-5 relative);
    # same pattern as K4 classical baselines (tol 1e-4). Aggregate below is still exact of stored reps.
    if not _close(fresh, stored0, tol=1e-4):
        print("❌ EXP-M12-001: frozen replication 0 does not reproduce results.json.")
        return False
    print("  ✅ frozen replication 0 reproduces results.json (relative tolerance 1e-4; wall_s excluded).")
    agg = json.loads(json.dumps(mod.aggregate(stored["replications"])))
    if not _close(agg, stored["aggregate"]):
        print("❌ EXP-M12-001: aggregate does not equal a fresh derivation from the stored replications.")
        return False
    print("  ✅ aggregate and hypothesis verdicts equal a fresh derivation from the stored replications.")
    report = mod.render_report(stored, float(stored.get("elapsed_s") or 0.0))
    if report != (exp / "REPORT.md").read_text():
        print("❌ EXP-M12-001: REPORT.md is not the render of results.json.")
        return False
    print("  ✅ REPORT.md equals a fresh render of results.json.")
    return True


def verify_k5_study() -> bool:
    print("🔬 Verifying EXP-K5-001 (K5 lab harmonisation) against committed results...")
    import importlib.util

    exp = ROOT / "experiments" / "EXP-K5-001"
    stored = json.loads((exp / "results.json").read_text())
    spec = importlib.util.spec_from_file_location("exp_k5_run_verify", exp / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_k5_run_verify"] = mod
    spec.loader.exec_module(mod)
    # (1) Re-run frozen replication 0 and compare every number.
    fresh = json.loads(json.dumps(mod.replication(("frozen", 0, stored["detector_calibration"], False))))
    if not _close(fresh, stored["replications"][0]):
        print("❌ EXP-K5-001: frozen replication 0 does not reproduce results.json.")
        return False
    print("  ✅ frozen replication 0 reproduces results.json (relative tolerance 1e-6; floats differ in the last digits across BLAS builds).")
    # (2) The aggregate and the hypothesis verdicts are a pure function of the stored replications.
    agg = json.loads(json.dumps(mod.aggregate(stored["replications"])))
    if not _close(agg, stored["aggregate"]):
        print("❌ EXP-K5-001: aggregate does not equal a fresh derivation from the stored replications.")
        return False
    print("  ✅ aggregate and hypothesis verdicts equal a fresh derivation from the stored replications.")
    # (3) REPORT.md is the render of results.json.
    report = mod.render_report(stored, stored["detector_calibration"], float(
        __import__("re").search(r"Run time (\d+) s", (exp / "REPORT.md").read_text()).group(1)))
    if report != (exp / "REPORT.md").read_text():
        print("❌ EXP-K5-001: REPORT.md is not the render of results.json.")
        return False
    print("  ✅ REPORT.md equals a fresh render of results.json.")
    return True


def verify_k4_study() -> bool:
    print("🔬 Verifying EXP-K4-001 (K4 deep families, pre-training, scale) against committed results...")
    import importlib.util

    exp = ROOT / "experiments" / "EXP-K4-001"
    stored = json.loads((exp / "results.json").read_text())
    spec = importlib.util.spec_from_file_location("exp_k4_run_verify", exp / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_k4_run_verify"] = mod
    spec.loader.exec_module(mod)
    # (1) The committed code is the code that produced the committed result.
    if stored["code_hash"] != mod.code_hash():
        print("❌ EXP-K4-001: k4.py or run.py changed after the frozen run (code hash differs); re-run or file an amendment.")
        return False
    print("  ✅ code hash of k4.py and run.py equals the hash recorded by the frozen run.")
    # (2) The aggregate and the verdicts are a pure function of the stored records.
    agg = json.loads(json.dumps(mod.aggregate(stored)))
    if not _close(agg, stored["aggregate"]):
        print("❌ EXP-K4-001: aggregate does not equal a fresh derivation from the stored records.")
        return False
    print("  ✅ aggregate and hypothesis verdicts equal a fresh derivation from the stored records.")
    # (3) REPORT.md is the render of results.json.
    if mod.render_report(stored) != (exp / "REPORT.md").read_text():
        print("❌ EXP-K4-001: REPORT.md is not the render of results.json.")
        return False
    print("  ✅ REPORT.md equals a fresh render of results.json.")
    # (4) The classical baselines of frozen replication 0 are regenerated from the seeds. (The neural arms are not
    # compared across machines: floating-point differences grow over epochs; same-machine determinism is tested.)
    fresh = json.loads(json.dumps(mod.unit_baselines("frozen", 0, "full")["records"]))
    old = [r for r in stored["records"] if r["rep"] == 0 and r["arm"] == "classical"]
    drop = ("train_seconds",)
    fresh = [{k: v for k, v in r.items() if k not in drop} for r in fresh]
    old = [{k: v for k, v in r.items() if k not in drop} for r in old]
    if not _close(fresh, old, tol=1e-4):
        print("❌ EXP-K4-001: classical baselines of frozen replication 0 do not reproduce results.json.")
        return False
    print("  ✅ classical baselines of frozen replication 0 reproduce results.json (relative tolerance 1e-4).")
    return True


def _k6_model_free_rep(mod) -> dict:
    """Frozen replication 0, fixed and stage-heuristic arms only: they need the alert thresholds
    (calibrated on the training world) and the test worlds, and no fitted model."""
    from vigil_ml import k6
    from vigil_ml import k6_engine as E
    from vigil_sim import GeneratorType
    from vigil_sim.surveillance import build_world

    cfg = mod.design("full")
    s = mod.base_seed("frozen", 0)
    train = build_world(GeneratorType.G1_SMOOTH, s, cfg["n_train_generated"])
    theta = k6.calibrate_thresholds(E.threshold_samples(train))
    stub = {"hazard": None, "prior": None, "table": None}
    gens = {"G1": (GeneratorType.G1_SMOOTH, 1), "G2": (GeneratorType.G2_BURST, 2), "G3": (GeneratorType.G3_NOISE, 3)}
    records = []
    for wname, (gen, off) in gens.items():
        world = build_world(gen, s + off, cfg["n_test_generated"])
        for fam, arm, params, factory in mod.arm_list(cfg, stub, full=(wname == "G1")):
            if fam not in ("fixed", "heuristic"):
                continue
            res = E.simulate(world, factory(), theta, k6.CostTable())
            records.append(mod._record("frozen", 0, wname, fam, arm, params, world, res))
    return {"records": records}


def verify_k6_study() -> bool:
    print("🔬 Verifying EXP-K6-001 (K6 active sensing) against committed results...")
    import importlib.util
    import os

    import xgboost  # noqa: F401  (imported before anything else that may load an OpenMP runtime)

    exp = ROOT / "experiments" / "EXP-K6-001"
    stored = json.loads((exp / "results.json").read_text())
    spec = importlib.util.spec_from_file_location("exp_k6_run_verify", exp / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_k6_run_verify"] = mod
    spec.loader.exec_module(mod)
    # (1) The stored results were produced by exactly this code (k6.py, k6_engine.py, surveillance.py, run.py).
    if stored.get("code_hash") != mod.code_hash():
        print("❌ EXP-K6-001: results.json was produced by different code than the committed code.")
        return False
    print("  ✅ results.json carries the hash of the committed code.")
    # (2) The aggregate and the hypothesis verdicts are a pure function of the stored records.
    agg = json.loads(json.dumps(mod.aggregate(stored)))
    if not _close(agg, stored["aggregate"]):
        print("❌ EXP-K6-001: aggregate does not equal a fresh derivation from the stored records.")
        return False
    print("  ✅ aggregate and hypothesis verdicts equal a fresh derivation from the stored records.")
    # (3) REPORT.md is the render of results.json.
    if mod.render_report(stored) != (exp / "REPORT.md").read_text():
        print("❌ EXP-K6-001: REPORT.md is not the render of results.json.")
        return False
    print("  ✅ REPORT.md equals a fresh render of results.json.")
    # (4) Re-run frozen replication 0 and compare every stored number of the arms that use no model
    #     (fixed and stage-heuristic). With VIGIL_VERIFY_K6_FULL=1 the whole replication is re-run, models included
    #     (about three minutes; tree-ensemble floats are only guaranteed on the same platform, hence opt-in).
    full = os.environ.get("VIGIL_VERIFY_K6_FULL") == "1"
    fresh = json.loads(json.dumps(mod.run_rep("frozen", 0, "full") if full else _k6_model_free_rep(mod)))
    keep = (lambda r: True) if full else (lambda r: r["family"] in ("fixed", "heuristic"))
    old = [r for r in stored["records"] if r["rep"] == 0 and keep(r)]
    new = [r for r in fresh["records"] if keep(r)]
    if not _close(new, old):
        print("❌ EXP-K6-001: frozen replication 0 does not reproduce results.json.")
        return False
    print(f"  ✅ frozen replication 0 reproduces results.json ({'all arms' if full else 'fixed and heuristic arms'}; relative tolerance 1e-6).")
    return True


def verify_ocr_study() -> bool:
    print("🔬 Verifying EXP-OCR-001 (PDF text-layer arm) against committed results...")
    import importlib.util

    exp = ROOT / "experiments" / "EXP-OCR-001"
    stored_path = exp / "results.json"
    report_path = exp / "REPORT.md"
    if not stored_path.exists() or not report_path.exists():
        print("❌ EXP-OCR-001: results.json or REPORT.md missing.")
        return False
    stored = json.loads(stored_path.read_text())
    spec = importlib.util.spec_from_file_location(
        "run_ocr_accuracy_verify", ROOT / "scripts" / "run_ocr_accuracy.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fresh = mod.evaluate(stored["seed"], images=False)
    if fresh["rates"]["pdf"] != stored["rates"]["pdf"]:
        print("❌ EXP-OCR-001: PDF exact-match rate does not reproduce results.json.")
        return False
    if fresh["hypotheses"]["H1_pdf_exact_ge_0.95"] != stored["hypotheses"]["H1_pdf_exact_ge_0.95"]:
        print("❌ EXP-OCR-001: H1 verdict does not reproduce results.json.")
        return False
    print("  ✅ PDF text-layer arm reproduces results.json.")
    if mod.render_report(stored) != report_path.read_text():
        print("❌ EXP-OCR-001: REPORT.md is not the render of results.json.")
        return False
    print("  ✅ REPORT.md equals a fresh render of results.json.")
    return True


def main() -> int:
    ok = True
    if not verify_ocr_study():
        ok = False
    if not verify_k4_study():
        ok = False
    if not verify_k6_study():
        ok = False
    if not verify_m12_study():
        ok = False
    if not verify_k5_study():
        ok = False
    if not verify_m10_reproducibility():
        ok = False
    if not verify_s8_k7_integrity():
        ok = False
    if not verify_m7_cpsat_v2():
        ok = False

    if not ok:
        print("\n❌ Study reproducibility verification failed.")
        return 1

    print("\n✅ All cheap study reproducibility and data integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
