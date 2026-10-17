#!/usr/bin/env python3
"""
scripts/generate_m5_journeys.py

Generates and validates the three canonical clinical worked journeys for Module M5:
  1. Journey J2: Surprising Result (Analytical Error) -> Adjudication -> Needs Repeat.
  2. Benign Fluctuation: Biological Variation within RCV -> Adjudication -> Explained.
  3. True Recurrence: Significant Biomarker Surge Exceeding RCV -> Adjudication -> Escalate.

Outputs reports/ml/M5_JOURNEYS.md.
"""

from __future__ import annotations

from pathlib import Path

from vigil_ml.m5 import generate_worked_journey

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "reports" / "ml" / "M5_JOURNEYS.md"


def main():
    journeys = [
        generate_worked_journey("j2_surprising_repeat"),
        generate_worked_journey("false_alarm_explained"),
        generate_worked_journey("real_progression_escalate"),
    ]

    lines = [
        "# Module M5: Verified Narrative Worked Clinical Journeys",
        "",
        "**Governing Documents:** `docs/MASTER_PLAN.md` §6.5, §14 WP4.2; `docs/ml/M3-M5-CONTRACT.md`; `docs/REALITY_RULES.md` RR7, RR14",
        "",
        "This document contains three canonical worked clinical journeys generated deterministically by `vigil_ml.m5.generate_worked_journey`. Each journey demonstrates the end-to-end integration of Module M3 (Plausibility Adjudication) with Module M5 (Provenance-Verified Narrative Generation). Every narrative was verified by `vigil_ml.m5.verify_narrative` without violations.",
        "",
        "---",
        "",
    ]

    for j in journeys:
        assert j["verification"]["ok"], (
            f"Verification failed for {j['journey_id']}: {j['verification']['violations']}"
        )
        lines.append(f"## {j['title']}")
        lines.append("")
        lines.append(f"**Journey Identifier:** `{j['journey_id']}`  ")
        lines.append(f"**Clinical Context:** {j['clinical_context']}  ")
        lines.append(f"**Adjudicated Action:** `{j['adjudication']['action']}`  ")
        lines.append("**Verification Status:** `PASSED` (Zero violations)")
        lines.append("")
        lines.append("### Structured Rationale Facts Table (Module M3)")
        lines.append("")
        lines.append("| Fact ID | Fact Type | Fact Value | Description |")
        lines.append("|---|---|---|---|")
        for f in j["adjudication"]["rationale_facts"]:
            val = f["value"]
            if isinstance(val, float):
                val_str = f"{val:.4f}"
            else:
                val_str = str(val)
            lines.append(
                f"| `{f['fact_id']}` | `{f['type']}` | **{val_str}** | Derived by Bayesian generative model |"
            )
        lines.append("")
        lines.append("### Generated Provenance-Verified Narrative (Module M5)")
        lines.append("")
        lines.append(f'> "{j["narrative"]}"')
        lines.append("")
        lines.append("---")
        lines.append("")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines))

    print(f"✅ Worked journeys successfully generated and verified at {OUT_PATH}")


if __name__ == "__main__":
    main()
