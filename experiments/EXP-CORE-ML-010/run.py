#!/usr/bin/env python3
"""One-time registered development-fit verification propensity study."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import sklearn
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "vigil-eval"))
from vigil_eval.verification_bias import evaluate_complete_case, evaluate_ipw_verification  # noqa: E402

EXP = Path(__file__).resolve().parent
N, REPLICATES, CUTOFF = 2500, range(100), 0.5
BASE, OFFSETS = 20261101, {"MCAR": 0, "MAR": 100000, "MNAR": 200000}
METRICS = (
    "empirical_sensitivity",
    "empirical_specificity",
    "apparent_prevalence",
    "brier_score",
    "roc_auc",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed(condition: str, rep: int, test: bool) -> int:
    return BASE + OFFSETS[condition] + (500000 if test else 0) + rep


def cohort(
    condition: str, rng: np.random.Generator, median: float | None = None
) -> dict[str, np.ndarray]:
    x = rng.normal(0, 1, N)
    y = rng.binomial(1, expit(-1 + 1.2 * x)).astype(int)
    marker = x + rng.normal(0, 0.5, N)
    marker_obs = rng.binomial(1, expit(-1 + 0.5 * x)).astype(bool)
    marker[~marker_obs] = np.nan
    med = float(np.nanmedian(marker)) if median is None else median
    if not np.isfinite(med):
        raise RuntimeError("No observed development marker; registered design invalid")
    missing = ~np.isfinite(marker)
    mi = np.where(missing, med, marker)
    lp = (
        np.full(N, np.log(0.6 / 0.4))
        if condition == "MCAR"
        else -0.5 + x + 0.4 * mi + 0.4 * missing
    )
    if condition == "MNAR":
        lp += 2 * y - 1
    verified = rng.binomial(1, expit(lp)).astype(bool)
    return {
        "x": x,
        "y": y,
        "risk": expit(-1 + 1.2 * x),
        "marker": marker,
        "mi": mi,
        "missing": missing,
        "verified": verified,
    }


def full_metrics(r: np.ndarray, y: np.ndarray) -> dict[str, float]:
    pos = y == 1
    neg = ~pos
    pred = r >= CUTOFF
    return {
        "empirical_sensitivity": float(np.mean(pred[pos])),
        "empirical_specificity": float(np.mean(~pred[neg])),
        "apparent_prevalence": float(np.mean(y)),
        "brier_score": float(np.mean((r - y) ** 2)),
        "roc_auc": float(roc_auc_score(y, r)),
    }


def one(condition: str, rep: int) -> dict[str, Any]:
    dev = cohort(condition, np.random.default_rng(seed(condition, rep, False)))
    test = cohort(
        condition,
        np.random.default_rng(seed(condition, rep, True)),
        float(np.nanmedian(dev["marker"])),
    )
    dm = np.column_stack((dev["x"], dev["mi"], dev["missing"].astype(float)))
    tm = np.column_stack((test["x"], test["mi"], test["missing"].astype(float)))
    model = LogisticRegression(max_iter=500).fit(dm, dev["verified"].astype(int))
    props = model.predict_proba(tm)[:, 1]
    verified = test["verified"]
    obs = np.where(verified, test["y"], np.nan)
    cc = evaluate_complete_case(test["risk"], obs, verified, CUTOFF)
    ipw = evaluate_ipw_verification(test["risk"], obs, verified, None, CUTOFF, props)
    if not ipw.details.get("metrics_defined"):
        raise RuntimeError(f"IPW undefined in {condition} replicate {rep}: {ipw.details}")
    truth = full_metrics(test["risk"], test["y"])
    estimates = {
        "complete_case": {m: float(getattr(cc, m)) for m in METRICS},
        "development_fit_ipw": {m: float(getattr(ipw, m)) for m in METRICS},
    }
    errors = {e: {m: estimates[e][m] - truth[m] for m in METRICS} for e in estimates}
    return {
        "condition": condition,
        "replicate": rep,
        "development_seed": seed(condition, rep, False),
        "test_seed": seed(condition, rep, True),
        "n_development": N,
        "n_test": N,
        "n_verified": int(verified.sum()),
        "reference": truth,
        "estimates": estimates,
        "errors": errors,
        "ipw_diagnostics": {
            "minimum_test_propensity": float(props.min()),
            "maximum_verified_inverse_weight": ipw.details["maximum_verified_inverse_weight"],
            "effective_sample_size": ipw.details["effective_sample_size"],
        },
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for c in OFFSETS:
        out[c] = {}
        cr = [r for r in rows if r["condition"] == c]
        for e in ("complete_case", "development_fit_ipw"):
            out[c][e] = {}
            for m in METRICS:
                err = np.array([r["errors"][e][m] for r in cr])
                est = np.array([r["estimates"][e][m] for r in cr])
                out[c][e][m] = {
                    "mean_estimate": float(est.mean()),
                    "mean_error": float(err.mean()),
                    "error_sd": float(err.std(ddof=1)),
                    "error_percentiles_2_5_97_5": [
                        float(x) for x in np.quantile(err, [0.025, 0.975])
                    ],
                    "n_defined": int(np.isfinite(err).sum()),
                    "n_total": len(err),
                }
    return out


def render(d: dict[str, Any]) -> str:
    lines = [
        "# EXP-CORE-ML-010: Development-fit verification propensity validation",
        "",
        "Synthetic method-validation only; no clinical or partner-data inference.",
        f"Source commit: `{d['source_commit']}`",
        "",
        "| Condition | Estimator | Metric | Mean error | Error SD | 95% error percentiles |",
        "|---|---|---|---:|---:|---:|",
    ]
    for c in OFFSETS:
        for e in ("complete_case", "development_fit_ipw"):
            for m, v in d["summary"][c][e].items():
                lo, hi = v["error_percentiles_2_5_97_5"]
                lines.append(
                    f"| {c} | {e} | {m} | {v['mean_error']:.6f} | {v['error_sd']:.6f} | [{lo:.6f}, {hi:.6f}] |"
                )
    lines += [
        "",
        "All replicate-level truth, estimates, errors and diagnostics are preserved in `results.json`. MCAR/MAR are the specified synthetic identification designs; MNAR is a negative control. Results do not validate exchangeability, positivity or mechanism stability in real cohorts.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    paths = [EXP / x for x in ("ACCESS_LOG.json", "results.json", "REPORT.md")]
    if any(p.exists() for p in paths):
        raise RuntimeError("One-time experiment output already exists; refusing overwrite")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    if status:
        raise RuntimeError("Refusing data access from a dirty working tree")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    access = {
        "experiment_id": "EXP-CORE-ML-010",
        "source_commit": commit,
        "preregistration_sha256": sha(EXP / "PREREG.md"),
        "runner_sha256": sha(Path(__file__)),
        "estimator_source_sha256": sha(
            ROOT / "packages/vigil-eval/vigil_eval/verification_bias.py"
        ),
        "partner_analysis_source_sha256": sha(ROOT / "scripts/partner_analysis.py"),
        "environment_lock_sha256": sha(ROOT / "uv.lock"),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scikit_learn_version": sklearn.__version__,
        "design": {"n_per_split": N, "replicates": len(REPLICATES), "conditions": OFFSETS},
        "completed": False,
    }
    paths[0].write_text(json.dumps(access, indent=2, sort_keys=True) + "\n")
    try:
        rows = [one(c, r) for c in OFFSETS for r in REPLICATES]
        result = {
            "experiment_id": "EXP-CORE-ML-010",
            "source_commit": commit,
            "design": access["design"],
            "summary": aggregate(rows),
            "replicates": rows,
        }
        paths[1].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        paths[2].write_text(render(result))
        access.update(
            {"completed": True, "results_sha256": sha(paths[1]), "report_sha256": sha(paths[2])}
        )
    except Exception as exc:
        access.update({"failure": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        paths[0].write_text(json.dumps(access, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
