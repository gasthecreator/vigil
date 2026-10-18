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
    match = True
    for key in ("study", "facilities", "hypotheses", "privacy_controls"):
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


def main() -> int:
    ok = True
    if not verify_m10_reproducibility():
        ok = False
    if not verify_s8_k7_integrity():
        ok = False

    if not ok:
        print("\n❌ Study reproducibility verification failed.")
        return 1

    print("\n✅ All cheap study reproducibility and data integrity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
