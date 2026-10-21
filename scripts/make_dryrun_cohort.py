#!/usr/bin/env python3
"""SYNTHETIC cohort in the partner extraction format, used to rehearse the partner evaluation end to end.

Two modes, both invented with a fixed seed:
  signal: 70 % of recurrent patients show an exponentially rising CA 15-3 in the year before the recurrence;
  null:   recurrence is independent of every laboratory value (the pipeline must then find nothing).
The generator does not import the analysis code. The result of running the analysis on this cohort is a plumbing
and null-behaviour check; it says nothing about performance on real patients.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from pathlib import Path

LOINC = {"ca_15_3": "83082-8", "alt": "1742-6", "ast": "1920-8"}
UNIT = {"ca_15_3": "[iU]/mL", "alt": "U/L", "ast": "U/L"}


def generate(out: Path, n: int, mode: str, seed: int) -> None:
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    pts, base, labs, outs = [], [], [], []
    for i in range(n):
        pid = f"SYN-{i + 1:05d}"
        follow = rng.randint(500, 1800)
        index = rng.randint(60, 200)
        recur = rng.random() < 0.30
        rday = rng.randint(index + 250, max(index + 251, follow)) if recur else None
        if rday is not None and rday > follow:
            recur, rday = False, None
        death_day = (
            rng.randint(rday + 1, follow)
            if recur and rday is not None and rday < follow and rng.random() < 0.3
            else None
        )
        rises = recur and mode == "signal" and rng.random() < 0.70
        dismissed = recur and rng.random() < 0.10
        age = rng.randint(30, 80)
        stage = rng.choice(["I", "IIA", "IIB", "IIIA", "IIIB"])
        er = rng.choice(["POSITIVE", "POSITIVE", "NEGATIVE"])
        pts.append(
            {
                "patient_id": pid,
                "age_at_diagnosis": age,
                "menopausal_status": "UNKNOWN",
                "vital_status": "DEAD_DISEASE" if death_day is not None else "ALIVE",
                "days_to_last_followup": follow,
                "days_to_death": death_day if death_day is not None else "",
                "index_day": index,
            }
        )
        base.append(
            {
                "patient_id": pid,
                "histological_type": "IDC",
                "tumor_grade": rng.randint(1, 3),
                "stage_ajcc": stage,
                "er_status": er,
                "pr_status": er,
                "her2_status": rng.choice(["POSITIVE", "NEGATIVE"]),
                "has_hypertension": "false",
                "renal_history": "false",
                "surgery_type": "MRM",
                "chemotherapy_given": "true",
                "endocrine_therapy": "true" if er == "POSITIVE" else "false",
                "radiotherapy_given": "true",
            }
        )
        base_ca = rng.lognormvariate(2.7, 0.3)
        doubling = rng.uniform(60, 120)
        day = index + rng.randint(0, 40)
        terminal_day = min(
            value for value in (rday, death_day, follow) if value is not None
        )
        elevated = False
        while day < terminal_day:
            ca = base_ca * math.exp(rng.gauss(0, 0.10))
            if rises and rday is not None and day > rday - 270:
                ca *= 2 ** ((day - (rday - 270)) / doubling)
            elevated = elevated or ca > 30
            for a, v in (
                ("ca_15_3", ca),
                ("alt", rng.lognormvariate(3.1, 0.3)),
                ("ast", rng.lognormvariate(3.1, 0.3)),
            ):
                labs.append(
                    {
                        "patient_id": pid,
                        "observation_day": day,
                        "analyte_code": LOINC[a],
                        "analyte_name": a,
                        "value_numeric": round(v, 2),
                        "unit_ucum": UNIT[a],
                        "ref_low": "",
                        "ref_high": "",
                    }
                )
            day += int(rng.gauss(90, 15))
        outs.append(
            {
                "patient_id": pid,
                "recurrence_confirmed": "true" if recur else "false",
                "recurrence_day": rday if recur else "",
                "site_bone": "true" if recur else "false",
                "site_liver": "false",
                "site_lung": "false",
                "site_brain": "false",
                "site_locoregional": "false",
                "confirmatory_modality": "CT_SCAN" if recur else "",
                "dismissed_prior_signal": "true" if dismissed else "false",
                "restaging_imaging_done": "true"
                if recur or (elevated and rng.random() < 0.7) or rng.random() < 0.15
                else "false",
            }
        )
    tables = {
        "patients": pts,
        "baseline_profile": base,
        "lab_observations": labs,
        "clinical_outcomes": outs,
    }
    for name, rows in tables.items():
        with (out / f"{name}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--patients", type=int, default=600)
    ap.add_argument("--mode", choices=("signal", "null"), default="signal")
    ap.add_argument("--seed", type=int, default=20261018)
    a = ap.parse_args()
    generate(a.out, a.patients, a.mode, a.seed)
    (a.out / "SYNTHETIC").write_text(
        f"All data in this folder are invented (scripts/make_dryrun_cohort.py, mode {a.mode}, seed {a.seed}).\n",
        encoding="utf-8",
    )
    print(f"wrote SYNTHETIC {a.mode} cohort of {a.patients} patients to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
