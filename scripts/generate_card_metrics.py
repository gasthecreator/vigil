#!/usr/bin/env python3
"""Write measured results from the committed study reports into model-card marker blocks (G-25).

No number in a card is typed by hand: each block below is generated from reports/ml/*.json.
  uv run python scripts/generate_card_metrics.py [--check | --seed-fail]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- measured:start -->", "<!-- measured:end -->"


def _load(name: str) -> dict:
    return json.loads((ROOT / "reports" / "ml" / name).read_text(encoding="utf-8"))


def m7() -> str:
    d = _load("STUDY_M7_DIGITAL_TWIN.json")
    b, h = d["baseline_summary"], d["hypotheses"]
    rows = "\n".join(
        f"| {arm} | {v['mean_harm']} | {v.get('mean_wait_days', 'n/a')} | {v.get('mean_subgroup_disparity_days', 'n/a')} |"
        for arm, v in b.items()
        if isinstance(v, dict) and "mean_harm" in v
    )
    return (
        f"Source: `reports/ml/STUDY_M7_DIGITAL_TWIN.json` (pre-registered `{d['pre_registration']}`; "
        f"{d['replications']} simulated replications; synthetic department, {d['facility']['linacs']} linacs). "
        "Simulation only: no clinical data.\n\n"
        "| Arm | Mean harm | Mean wait (days) | Subgroup disparity (days) |\n|---|---|---|---|\n"
        f"{rows}\n\n"
        f"- H1 (CP-SAT lower harm than FCFS): **{h['H1_harm_reduction_vs_fcfs']['verdict']}** "
        f"(mean difference {h['H1_harm_reduction_vs_fcfs']['observed_mean_diff']}, "
        f"95% CI {h['H1_harm_reduction_vs_fcfs']['bootstrap_95_ci']}).\n"
        f"- H2 (CP-SAT vs urgency heuristic): **{h['H2_cpsat_vs_urgency_heuristic']['verdict']}** "
        f"(mean difference {h['H2_cpsat_vs_urgency_heuristic']['observed_mean_diff']}).\n"
        "- Consequence: CP-SAT is research-only; the shipped default is the explainable urgency ranking."
    )


def k7() -> str:
    d = _load("STUDY_S8_K7_CAUSAL.json")
    b, h = d["scenario_b_unmeasured_confounding"], d["hypotheses"]
    h1, h2 = h["H1_ground_truth_recovery"], h["H2_covariate_balance"]
    be = b["estimates"]
    return (
        f"Source: `reports/ml/STUDY_S8_K7_CAUSAL.json` (pre-registered `{d['pre_registration']}`; "
        f"n = {d['sample_size']} synthetic, {d['bootstrap_replications']} bootstrap replications).\n\n"
        f"- Measured confounding: true RR {h1['true_rr']}; AIPW {h1['aipw_rr']} (95% CI {h1['aipw_ci_95']}), "
        f"naive {h1['naive_rr']}: **{h1['verdict']}**. Max weighted SMD {h2['max_weighted_smd']} "
        f"(threshold {h2['threshold']}): **{h2['verdict']}**.\n"
        f"- Unmeasured confounding: true RR {b['ground_truth_marginal_rr']}; naive {be['naive']['rr']}, "
        f"IPTW {be['iptw']['rr']}, AIPW {be['aipw']['rr']} (95% CI {be['aipw']['ci_95']}). "
        "**All estimators are biased; adjustment does not rescue unmeasured confounding.** "
        f"E-value {b['sensitivity_e_values']['e_value_estimate']} "
        f"(CI bound {b['sensitivity_e_values']['e_value_ci_lower']}) only quantifies how strong a confounder would need to be.\n"
        "- The module outputs sensitivity analysis, not a causal claim, on real data."
    )


def m10() -> str:
    d = _load("STUDY_M10_MISSED_SIGNALS.json")
    h, p = d["hypotheses_evaluation"], d["privacy_and_governance"]
    rows = "\n".join(f"| {k} | {v['status']} |" for k, v in h.items())
    return (
        f"Source: `reports/ml/STUDY_M10_MISSED_SIGNALS.json` (pre-registered `{d['pre_registration']}`; synthetic "
        "facilities with injected ground truth).\n\n"
        f"| Hypothesis | Status |\n|---|---|\n{rows}\n\n"
        f"- Sensitivity {h['H1_sensitivity_precision']['sensitivity_point']:.3f}, precision "
        f"{h['H1_sensitivity_precision']['precision_point']:.3f}; mean delay error "
        f"{h['H2_delay_accuracy']['mean_delay_error_days']:.1f} days.\n"
        f"- Privacy: k-anonymity floor {p['k_anonymity_floor']}, neutral register verified: {p['neutral_register_verified']}.\n"
        "- These are synthetic-data results with injected signals; they say nothing about real-world performance."
    )


def ocr() -> str:
    d = json.loads(
        (ROOT / "experiments" / "EXP-OCR-001" / "results.json").read_text(encoding="utf-8")
    )
    r = d["rates"]
    rows = "\n".join(f"| {k} | {v:.3f} |" for k, v in sorted(r.items()))
    hyp = ", ".join(f"{k}: {'met' if v['met'] else 'NOT met'}" for k, v in d["hypotheses"].items())
    return (
        f"Source: `experiments/EXP-OCR-001/results.json` (synthetic lab reports, n = {d['n']}, Tesseract; "
        f"kill rule fired: {d['kill_fired']}).\n\n"
        f"| Condition | Exact-match rate |\n|---|---|\n{rows}\n\n"
        f"- Pre-registered criteria: {hyp}.\n"
        "- Synthetic, rendered text only: real scans, handwriting and other layouts are untested. The human confirm gate "
        "stays mandatory whatever these rates are."
    )


CARDS = {
    "MODEL-CARD-OCR.md": ocr,
    "MODEL-CARD-M7.md": m7,
    "MODEL-CARD-K7.md": k7,
    "MODEL-CARD-M10.md": m10,
}


def apply(text: str, block: str) -> str:
    body = f"{START}\n## Measured results (script-written)\n\n{block}\n{END}"
    if START in text:
        return text[: text.index(START)] + body + text[text.index(END) + len(END) :]
    return text.rstrip("\n") + "\n\n" + body + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed-fail", action="store_true")
    args = ap.parse_args()
    stale = []
    for name, fn in CARDS.items():
        path = ROOT / "docs" / "models" / name
        have = path.read_text(encoding="utf-8")
        want = apply(have, fn())
        if args.seed_fail:  # simulate a hand-edited number inside the generated block
            s, e = have.find(START), have.find(END)
            have = (
                have[:s] + have[s:e].replace("0.", "9.", 1) + have[e:]
                if s != -1
                else have + "\nmissing block"
            )
        if args.check or args.seed_fail:
            if have != want:
                stale.append(name)
        else:
            path.write_text(want, encoding="utf-8")
    if args.check or args.seed_fail:
        if stale:
            print(f"❌ card metrics stale or hand-edited: {stale}", file=sys.stderr)
            return 1
        print("✅ card metrics are fresh")
        return 0
    print(f"Wrote measured blocks into {len(CARDS)} model cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
