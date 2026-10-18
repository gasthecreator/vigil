#!/usr/bin/env python3
"""Compare baseline marginals of the simulator with METABRIC and TCGA-BRCA. Writes reports/data/MARGINALS_PUBLIC_VS_SIM.{json,md}.

Needs the files of scripts/fetch_public_clinical.py in data/external/ (network, not committed). The simulator's baseline
sampler (`BaseCohortGenerator.sample_nigerian_baseline`) is parameterised from Nigerian priors (docs/EVIDENCE.md), not
fitted to either public cohort, so differences are expected. This report measures how far apart they are so that nobody
mistakes the simulator for a fit to METABRIC or TCGA. It does not validate the simulator.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "external"
OUT = ROOT / "reports" / "data"
N_SIM = 5000
SEED = 20261018

from contracts.loaders.cbioportal import load_study  # noqa: E402
from vigil_sim.generators import ContinuousSecretionGenerator  # noqa: E402


def sim_frame() -> pd.DataFrame:
    g = ContinuousSecretionGenerator(seed=SEED)
    rows = []
    for i in range(N_SIM):
        b = g.sample_nigerian_baseline(i)
        rows.append(
            {
                "age": b.age,
                "stage": b.stage.value.replace("Stage ", ""),
                "er": b.er_status,
                "pr": b.pr_status,
                "her2": b.her2_status,
                "subtype": b.subtype.value,
            }
        )
    return pd.DataFrame(rows)


def frac(s: pd.Series, value) -> float:
    s = s.dropna()
    return float((s == value).mean()) if len(s) else float("nan")


def summarise(
    name: str, df: pd.DataFrame, age_col: str, stage_col: str, er, pr, her2, subtype_map
) -> dict:
    out = {
        "n": int(len(df)),
        "age_mean": float(df[age_col].mean()),
        "age_sd": float(df[age_col].std()),
        "age_quantiles_10_50_90": [float(x) for x in df[age_col].quantile([0.1, 0.5, 0.9])],
    }
    st = df[stage_col].dropna()
    out["stage_known"] = int(len(st))
    out["stage_fraction"] = {k: float((st == k).mean()) for k in ("I", "II", "III", "IV")}
    for key, col, pos in (
        ("er_positive", er[0], er[1]),
        ("pr_positive", pr[0], pr[1]),
        ("her2_positive", her2[0], her2[1]),
    ):
        known = df[col].dropna() if col in df else pd.Series(dtype=object)
        out[key] = {
            "known": int(len(known)),
            "fraction": float((known == pos).mean()) if len(known) else None,
        }
    sub = df["subtype"].map(subtype_map).dropna()
    out["subtype_fraction"] = (
        {k: float((sub == k).mean()) for k in ("TNBC-like", "HER2+", "HR+HER2-")}
        if len(sub)
        else {}
    )
    out["subtype_known"] = int(len(sub))
    return out


def main() -> int:
    files = {
        "METABRIC": ("METABRIC_patient.tsv", "METABRIC_sample.tsv"),
        "TCGA-BRCA": ("TCGA-BRCA_patient.tsv", "TCGA-BRCA_sample.tsv"),
    }
    if not all((EXT / f).exists() for pair in files.values() for f in pair):
        print(
            "data/external is missing; run scripts/fetch_public_clinical.py first (network required)",
            file=sys.stderr,
        )
        return 1
    res: dict = {
        "synthetic_vs_public": True,
        "simulator": {
            "generator": "ContinuousSecretionGenerator.sample_nigerian_baseline",
            "seed": SEED,
            "n": N_SIM,
        },
        "sources": {},
        "loader_reports": {},
    }
    sim = sim_frame()
    sim_out = summarise(
        "sim",
        sim,
        "age",
        "stage",
        ("er", True),
        ("pr", True),
        ("her2", True),
        {"TNBC": "TNBC-like", "HER2+": "HER2+", "HR+HER2-": "HR+HER2-"},
    )
    res["marginals"] = {"simulator (Nigerian priors, SYNTHETIC)": sim_out}
    ages = {"simulator": sim["age"].to_numpy()}
    for label, (pf, sf) in files.items():
        df, rep = load_study(label, EXT / pf, EXT / sf)
        res["loader_reports"][label] = {k: v for k, v in rep.items() if k != "rejections"}
        res["sources"][label] = {
            pf: hashlib.sha256((EXT / pf).read_bytes()).hexdigest(),
            sf: hashlib.sha256((EXT / sf).read_bytes()).hexdigest(),
        }
        if label == "METABRIC":
            sm = {
                "Basal": "TNBC-like",
                "claudin-low": "TNBC-like",
                "Her2": "HER2+",
                "LumA": "HR+HER2-",
                "LumB": "HR+HER2-",
            }
        else:
            sm = {
                "BRCA_Basal": "TNBC-like",
                "BRCA_Her2": "HER2+",
                "BRCA_LumA": "HR+HER2-",
                "BRCA_LumB": "HR+HER2-",
            }
        res["marginals"][label] = summarise(
            label,
            df,
            "age_years",
            "stage",
            ("er", "POSITIVE"),
            ("pr", "POSITIVE"),
            ("her2", "POSITIVE"),
            sm,
        )
        ages[label] = df["age_years"].dropna().to_numpy()
        ks = ks_2samp(ages["simulator"], ages[label])
        res["marginals"][label]["age_ks_vs_simulator"] = {
            "statistic": float(ks.statistic),
            "p_value": float(ks.pvalue),
        }
    res["notes"] = [
        "Subtype for the public cohorts is the PAM50/Claudin-low label mapped to receptor-style groups (Basal and claudin-low to TNBC-like); the simulator draws receptor-style groups directly. The mapping is approximate and is the reader's to judge.",
        "Stage fractions use stage-known patients only; METABRIC stage 0 is excluded from the four-way split. METABRIC and TCGA are surgical cohorts, so stage IV is rare by design; the simulator's stage IV share is a de novo metastatic presentation prior.",
        "TCGA-BRCA PanCancer Atlas clinical attributes carry no receptor status, so TCGA receptor rows are empty.",
        "Differences are expected. The simulator's priors come from the Nigerian evidence in docs/EVIDENCE.md (E7, E12; both currently graded SECONDARY), not from these cohorts; the report quantifies the gap and does not claim the simulator fits any of them.",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "MARGINALS_PUBLIC_VS_SIM.json").write_text(
        json.dumps(res, indent=2) + "\n", encoding="utf-8"
    )
    cols = list(res["marginals"])
    L = [
        "# Baseline marginals: simulator vs METABRIC vs TCGA-BRCA",
        "",
        "> Written by `scripts/compare_marginals_public_vs_sim.py`; do not edit by hand. The simulator column is **synthetic**; the others are public registry data downloaded with `scripts/fetch_public_clinical.py` (hashes in the JSON). This is a distance measurement, not a validation.",
        "",
        "| quantity | " + " | ".join(cols) + " |",
        "|---|" + "---:|" * len(cols),
    ]

    def row(label, f):
        L.append(f"| {label} | " + " | ".join(f(res["marginals"][c]) for c in cols) + " |")

    row("patients", lambda m: str(m["n"]))
    row("age mean (sd)", lambda m: f"{m['age_mean']:.1f} ({m['age_sd']:.1f})")
    row(
        "age 10th / 50th / 90th",
        lambda m: " / ".join(f"{x:.0f}" for x in m["age_quantiles_10_50_90"]),
    )
    for k in ("I", "II", "III", "IV"):
        row(
            f"stage {k}",
            lambda m, k=k: f"{100 * m['stage_fraction'][k]:.1f} % (of {m['stage_known']})",
        )
    for k, nm in (("er_positive", "ER+"), ("pr_positive", "PR+"), ("her2_positive", "HER2+")):
        row(
            nm,
            lambda m, k=k: (
                "n/a"
                if not m[k]["known"]
                else f"{100 * m[k]['fraction']:.1f} % (of {m[k]['known']})"
            ),
        )
    for k in ("TNBC-like", "HER2+", "HR+HER2-"):
        row(
            f"subtype {k}",
            lambda m, k=k: f"{100 * m['subtype_fraction'].get(k, float('nan')):.1f} %",
        )
    row(
        "age KS vs simulator",
        lambda m: (
            "-"
            if "age_ks_vs_simulator" not in m
            else f"D = {m['age_ks_vs_simulator']['statistic']:.2f}"
        ),
    )
    L += [
        "",
        "## Loader reports (real files)",
        "",
        "| study | patients in file | loaded | rows rejected | rejections by code:field |",
        "|---|---:|---:|---:|---|",
    ]
    for s, r in res["loader_reports"].items():
        L.append(
            f"| {s} | {r['patients_in_file']} | {r['patients_loaded']} | {r['rows_rejected']} | {r['rejections_by_code_and_field'] or 'none'} |"
        )
    L += ["", "## Notes", "", *[f"- {n}" for n in res["notes"]], ""]
    (OUT / "MARGINALS_PUBLIC_VS_SIM.md").write_text("\n".join(L), encoding="utf-8")
    print("wrote", OUT / "MARGINALS_PUBLIC_VS_SIM.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
