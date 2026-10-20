#!/usr/bin/env python3
"""Verify reproducible outputs and integrity of preserved study artifacts.

K4/K5/K6/M7/M12 aggregates and reports are re-derived only from committed result
records. Their frozen cohorts are not replayed. Invalidated historical artifacts
must carry explicit provenance and status records.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
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
    print("🔬 Verifying EXP-M7-001 stored artifacts (no frozen replay)...")
    exp = ROOT / "experiments" / "EXP-M7-001"
    runner_path = ROOT / "scripts" / "run_study_m7_cpsat_v2.py"
    spec = importlib.util.spec_from_file_location("exp_m7_run_verify", runner_path)
    if spec is None or spec.loader is None:
        print("❌ EXP-M7-001: could not load report renderer.")
        return False
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = json.loads((exp / "results.json").read_text())
    development = json.loads((exp / "dev_results.json").read_text())
    expected_report = mod.render_report(result, development)
    stored_report = (exp / "REPORT.md").read_text()
    if _canonical_m7_report(expected_report) != _canonical_m7_report(stored_report):
        print("❌ EXP-M7-001: REPORT.md is not the render of the preserved result records.")
        return False
    print("  ✅ REPORT.md equals a fresh render of the preserved result records.")
    # Re-derive the all-in analysis from results.json in-process; no simulation or solver.
    sys.path.insert(0, str(ROOT / "scripts"))
    from analyze_m7_cpsat_v2_allin import analyse

    derived = analyse(result)
    committed = json.loads((exp / "ALLIN_ANALYSIS.json").read_text())
    if json.loads(json.dumps(derived, sort_keys=True)) != committed:
        print("❌ ALLIN_ANALYSIS.json does not match a fresh derivation from results.json (stale or hand-edited).")
        return False
    print("  ✅ ALLIN_ANALYSIS.json equals a fresh derivation from results.json.")
    return True


def _canonical_m7_report(report: str) -> str:
    """Ignore JSON key ordering in historical table rows while comparing every value."""
    rows = []
    other = []
    for line in report.splitlines():
        if not line.startswith("| lambda_"):
            other.append(line)
            continue
        columns = line.split("|")
        for index, column in enumerate(columns):
            value = column.strip()
            if value.startswith("{"):
                parsed = ast.literal_eval(value)
                columns[index] = " " + repr(dict(sorted(parsed.items()))) + " "
        rows.append("|".join(columns))
    return "\n".join(other + sorted(rows)) + "\n"


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


def verify_alert_fatigue_history() -> bool:
    """Check the preserved EXP-UF-001 artifact without replaying its consumed seed."""
    print("🔬 Verifying EXP-UF-001 historical artifact integrity (no seed replay)...")
    exp = ROOT / "reports" / "usability" / "alert-fatigue"
    result_path = exp / "results.json"
    report_path = exp / "REPORT.md"
    status_path = exp / "RECONCILIATION.md"
    if not all(path.exists() for path in (result_path, report_path, status_path)):
        print("❌ EXP-UF-001: result, report, or historical reconciliation is missing.")
        return False

    result = json.loads(result_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")
    status = status_path.read_text(encoding="utf-8")
    hashes = {
        "results.json": hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "REPORT.md": hashlib.sha256(report_path.read_bytes()).hexdigest(),
    }
    for filename, digest in hashes.items():
        if f"`{filename}` SHA-256: `{digest}`" not in status:
            print(f"❌ EXP-UF-001: preserved {filename} does not match its reconciliation hash.")
            return False
    if "historical; not current evidence" not in status.lower():
        print("❌ EXP-UF-001: stale result is not explicitly marked historical.")
        return False
    if result.get("seed") != 1624 or result.get("data_status", "").split(";")[0] != "SYNTHETIC":
        print("❌ EXP-UF-001: preserved result metadata does not match its preregistration.")
        return False

    report_fields = {
        "patients_with_observed_ca_15_3": f"- Patients with observed CA 15-3: {result['patients_with_observed_ca_15_3']}",
        "patients_with_latched_alert": f"- Patients with a latched alert: {result['patients_with_latched_alert']}",
        "fraction_with_latched_alert": f"- Fraction with a latched alert: {result['fraction_with_latched_alert']}",
        "observed_ca_15_3_count": f"- Observed CA 15-3 values processed: {result['observed_ca_15_3_count']}",
    }
    if any(line not in report for line in report_fields.values()):
        print("❌ EXP-UF-001: REPORT.md disagrees with its preserved results.json.")
        return False
    for key, value in (("observed streams", 246), ("latched alerts", 44), ("observations", 979)):
        if str(value) not in status:
            print(f"❌ EXP-UF-001: reconciliation omits the audited current-source {key} count.")
            return False
    print("  ✅ preserved report/result agree and the current-source mismatch is disclosed.")
    return True


def verify_m12_study() -> bool:
    print("🔬 Verifying EXP-M12-001 historical artifact integrity (no frozen replay)...")
    import importlib.util

    exp = ROOT / "experiments" / "EXP-M12-001"
    stored = json.loads((exp / "results.json").read_text())
    spec = importlib.util.spec_from_file_location("exp_m12_run_verify", exp / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_m12_run_verify"] = mod
    spec.loader.exec_module(mod)
    status = (exp / "PROVENANCE-AND-CONTRACT-AUDIT.md").read_text()
    conclusion = (exp / "CONCLUSION.md").read_text()
    if "historical, provenance-incomplete, and not current model-selection evidence" not in status:
        print("❌ EXP-M12-001: historical invalidation status is missing.")
        return False
    if "Do not use H1–H4" not in conclusion:
        print("❌ EXP-M12-001: conclusion does not withhold the invalid historical findings.")
        return False
    print("  ✅ invalid historical status is explicit; frozen training/evaluation was not replayed.")
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
    print("🔬 Verifying EXP-K5-001 stored aggregates and report (no frozen replay)...")
    import importlib.util

    exp = ROOT / "experiments" / "EXP-K5-001"
    stored = json.loads((exp / "results.json").read_text())
    spec = importlib.util.spec_from_file_location("exp_k5_run_verify", exp / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_k5_run_verify"] = mod
    spec.loader.exec_module(mod)
    # The frozen run is single-access. Re-derive only from stored replication records.
    agg = json.loads(json.dumps(mod.aggregate(stored["replications"])))
    if not _close(agg, stored["aggregate"]):
        print("❌ EXP-K5-001: aggregate does not equal a fresh derivation from the stored replications.")
        return False
    print("  ✅ aggregate and hypothesis verdicts equal a fresh derivation from the stored replications.")
    # REPORT.md is re-derived from results.json and its preserved runtime field.
    import re

    report_path = exp / "REPORT.md"
    report_text = report_path.read_text()
    runtime = re.search(r"Run time (\d+) s", report_text)
    if runtime is None:
        print("❌ EXP-K5-001: REPORT.md does not record its runtime.")
        return False
    report = mod.render_report(stored, stored["detector_calibration"], float(runtime.group(1)))
    if report != report_text:
        print("❌ EXP-K5-001: REPORT.md is not the render of results.json.")
        return False
    print("  ✅ REPORT.md equals a fresh render of results.json.")
    return True


def verify_k4_study() -> bool:
    print("🔬 Verifying EXP-K4-001 historical artifact integrity (no frozen replay)...")
    import importlib.util

    exp = ROOT / "experiments" / "EXP-K4-001"
    stored = json.loads((exp / "results.json").read_text())
    spec = importlib.util.spec_from_file_location("exp_k4_run_verify", exp / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_k4_run_verify"] = mod
    spec.loader.exec_module(mod)
    # The original source hash and missing access-log status are recorded; the
    # frozen run must not be repeated to make current source hashes match.
    history = (exp / "FROZEN-SEEDS-SPENT.md").read_text()
    if stored.get("code_hash") not in history or "Preserve these artifacts; do not rerun" not in history:
        print("❌ EXP-K4-001: historical code hash or no-replay disposition is missing.")
        return False
    if "access record is incomplete" not in history:
        print("❌ EXP-K4-001: missing frozen-access provenance is not disclosed.")
        return False
    print("  ✅ historical source hash and incomplete access status are explicit; no frozen cohort was replayed.")
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
    return True


def verify_k6_study() -> bool:
    print("🔬 Verifying EXP-K6-001 historical artifact integrity (no frozen replay)...")
    import importlib.util

    exp = ROOT / "experiments" / "EXP-K6-001"
    stored = json.loads((exp / "results.json").read_text())
    spec = importlib.util.spec_from_file_location("exp_k6_run_verify", exp / "run.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_k6_run_verify"] = mod
    spec.loader.exec_module(mod)
    conclusion = (exp / "CONCLUSION.md").read_text()
    replay_audit = (exp / "PROVENANCE-AND-REPLAY-AUDIT.md").read_text()
    if stored.get("code_hash") not in conclusion:
        print("❌ EXP-K6-001: historical source hash is missing from the conclusion.")
        return False
    if "No K6 cohort was generated" not in replay_audit:
        print("❌ EXP-K6-001: no-replay provenance is not documented.")
        return False
    print("  ✅ historical source hash and no-replay provenance are explicit.")
    # Re-derive aggregates and reports only from the committed records.
    agg = json.loads(json.dumps(mod.aggregate(stored)))
    if not _close(agg, stored["aggregate"]):
        print("❌ EXP-K6-001: aggregate does not equal a fresh derivation from the stored records.")
        return False
    print("  ✅ aggregate and hypothesis verdicts equal a fresh derivation from the stored records.")
    # REPORT.md is the render of results.json.
    if mod.render_report(stored) != (exp / "REPORT.md").read_text():
        print("❌ EXP-K6-001: REPORT.md is not the render of results.json.")
        return False
    print("  ✅ REPORT.md equals a fresh render of results.json.")
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
    if not verify_alert_fatigue_history():
        ok = False
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
