#!/usr/bin/env python3
"""Precision-based sample sizes for sensitivity/specificity-type proportions. Writes docs/clinical/SAMPLE-SIZE.md.

For a proportion p estimated from n independent binary outcomes, the smallest n whose two-sided 95 % Wilson interval
has half-width <= d. Events needed for a sensitivity claim are n_wilson(sens, d); patients needed are events / outcome
prevalence over the horizon. This is the *precision* criterion only. The Riley et al. criteria for prediction-model
development (shrinkage, optimism, overall risk) need the candidate parameter count, anticipated R^2 and outcome
prevalence from the partner and are NOT computed here (docs/HANDOVER.md lists the input needed).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

Z = 1.959963984540054  # two-sided 95 %
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "clinical" / "SAMPLE-SIZE.md"


def _check(p: float, d: float) -> None:
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    if not 0.0 < d < 0.5:
        raise ValueError("d must be in (0, 0.5)")


def n_normal(p: float, d: float) -> int:
    _check(p, d)
    return math.ceil(Z * Z * p * (1 - p) / (d * d))


def wilson_halfwidth(p: float, n: int) -> float:
    if n < 1:
        return float("inf")
    z2 = Z * Z
    return (Z / (1 + z2 / n)) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))


def n_wilson(p: float, d: float) -> int:
    _check(p, d)
    n = max(1, n_normal(p, d) // 2)
    while wilson_halfwidth(p, n) > d:
        n += 1
    while n > 1 and wilson_halfwidth(p, n - 1) <= d:
        n -= 1
    return n


def patients_for_events(events: int, prevalence: float) -> int:
    if not 0.0 < prevalence <= 1.0:
        raise ValueError("prevalence must be in (0, 1]")
    return math.ceil(events / prevalence)


def render() -> str:
    sens = (0.70, 0.80, 0.90)
    halfw = (0.05, 0.10, 0.15)
    prev = (0.05, 0.10, 0.20)
    L = [
        "# Sample size: precision criterion (SYNTHETIC ASSUMPTIONS, no partner data)", "",
        "> Written by `scripts/sample_size_precision.py`. Do not edit by hand. These are arithmetic consequences of assumed sensitivities, interval half-widths and outcome prevalences; no value here is an estimate from real data.", "",
        "Events needed so that the 95 % Wilson interval for a sensitivity of `p` has half-width at most `d`:", "",
        "| assumed sensitivity | d = 0.05 | d = 0.10 | d = 0.15 |", "|---|---:|---:|---:|",
    ]
    for p in sens:
        L.append(f"| {p:.2f} | " + " | ".join(str(n_wilson(p, d)) for d in halfw) + " |")
    L += ["", "Patients needed for `E` events at a given 365-day outcome prevalence (patients = events / prevalence; ignores loss to follow-up, so a lower bound):", "",
          "| events | prevalence 0.05 | prevalence 0.10 | prevalence 0.20 |", "|---|---:|---:|---:|"]
    for p, d in ((0.8, 0.10), (0.8, 0.05), (0.9, 0.05)):
        e = n_wilson(p, d)
        L.append(f"| {e} (sens {p:.2f}, d {d:.2f}) | " + " | ".join(str(patients_for_events(e, v)) for v in prev) + " |")
    L += ["", f"PR-05 (minimum events for a subgroup estimate) in `PREREGISTRATION.md` is proposed as 20; with an assumed sensitivity of 0.80 that gives a Wilson half-width of {wilson_halfwidth(0.8, 20):.3f}, which is why a subgroup below it is reported as insufficient.", "",
          "Not computed (blocked on partner inputs, see `docs/HANDOVER.md`): Riley et al. criteria for prediction-model development; competing-risk and censoring inflation of the required patient count.", ""]
    return "\n".join(L)


def main() -> int:
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
