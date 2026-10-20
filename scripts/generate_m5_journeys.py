#!/usr/bin/env python3
"""
scripts/generate_m5_journeys.py

Generates and validates three illustrative synthetic M3/M5 scenarios. Their names
describe generated inputs and model outputs, not clinical truth or model validity.

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
        "# Module M5: Synthetic Illustrations of Structured-Fact Narratives",
        "",
        "**Governing Documents:** `docs/MASTER_PLAN.md` §6.5, §14 WP4.2; `docs/ml/M3-M5-CONTRACT.md`; `docs/REALITY_RULES.md` RR7, RR14",
        "",
        "This document contains three illustrative synthetic scenarios generated deterministically by `vigil_ml.m5.generate_worked_journey`. The values and scenario labels are not clinical observations or ground-truth evidence for model performance. M3 outputs are conditional on unvalidated model assumptions; M5 verification checks that narrative sentences match structured facts, not whether those facts are medically correct. Nothing here establishes recurrence, benignity, analytical error, or clinical utility.",
        "",
        "---",
        "",
    ]

    for j in journeys:
        assert j["synthetic"] is True and j["evidence_status"] == "illustrative_only"
        assert j["verification"]["ok"], (
            f"Verification failed for {j['journey_id']}: {j['verification']['violations']}"
        )
        lines.append(f"## {j['title']}")
        lines.append("")
        lines.append(f"**Journey Identifier:** `{j['journey_id']}`")
        lines.append("**Evidence status:** `synthetic illustration only`")
        lines.append(f"**Synthetic scenario:** {j['clinical_context']}")
        lines.append(f"**M3 model output:** `{j['adjudication']['action']}`")
        lines.append("**M5 fact-to-text check:** `PASSED` (zero template derivation violations; this is not model validation)")
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
                f"| `{f['fact_id']}` | `{f['type']}` | **{val_str}** | Experimental M3 output under fixed illustrative assumptions |"
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
