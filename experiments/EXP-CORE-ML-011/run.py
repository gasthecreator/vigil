#!/usr/bin/env python3
"""One-time runner for EXP-CORE-ML-011 synthetic simulator mechanism checks."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy.stats import kstest, poisson

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "vigil-sim"))

from vigil_sim.generators import GeneratorType, get_generator  # noqa: E402
from vigil_sim.mechanisms import draw_poisson_event_times, patient_rng  # noqa: E402

HERE = Path(__file__).resolve().parent
PROFILE_PATH = ROOT / "packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json"
PREREG_PATH = HERE / "PREREG.md"
LOCK_PATH = ROOT / "uv.lock"
OUTPUTS = (HERE / "ACCESS_LOG.json", HERE / "results.json", HERE / "REPORT.md")
BASE_SEED = 20261101
COHORT_SIZE = 1000
REPLICATES = 5
DURATION_DAYS = 730.0


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def poisson_two_sided_exact(observed: int, expected: float) -> float:
    """Probability-ordering exact two-sided Poisson test."""
    if expected <= 0:
        return 1.0 if observed == 0 else 0.0
    upper = int(np.ceil(expected + 14.0 * np.sqrt(expected) + 100.0))
    support = np.arange(upper + 1)
    probabilities = poisson.pmf(support, expected)
    observed_probability = float(poisson.pmf(observed, expected))
    return min(
        1.0, float(probabilities[probabilities <= observed_probability * (1.0 + 1e-12)].sum())
    )


def rk4_constant_burden(
    start: float, end: float, initial: float, burden: float, secretion: float, clearance: float
) -> float:
    """Independent fixed-step RK4 reference for the registered linear ODE."""
    state = initial
    elapsed = start
    while elapsed < end:
        step = min(0.01, end - elapsed)

        def derivative(value: float) -> float:
            return secretion * burden - clearance * value

        k1 = derivative(state)
        k2 = derivative(state + step * k1 / 2.0)
        k3 = derivative(state + step * k2 / 2.0)
        k4 = derivative(state + step * k3)
        state += step * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
        elapsed += step
    return state


def validate_g1_transitions(seed: int) -> dict[str, float | int | bool]:
    rng = np.random.default_rng(seed)
    from vigil_sim.mechanisms import propagate_first_order_secretion

    errors: list[float] = []
    for _ in range(1000):
        start = float(rng.uniform(0.0, 600.0))
        interval = float(rng.uniform(0.01, 90.0))
        initial = float(rng.uniform(0.0, 200.0))
        burden = float(rng.uniform(0.0, 100.0))
        secretion = float(rng.uniform(0.0, 1.0))
        clearance = float(rng.uniform(0.001, 0.2))
        actual = float(
            propagate_first_order_secretion(
                [start, start + interval], [burden], initial, secretion, clearance
            )[-1]
        )
        reference = rk4_constant_burden(
            start, start + interval, initial, burden, secretion, clearance
        )
        errors.append(abs(actual - reference))
    maximum_error = max(errors)
    return {
        "cases": len(errors),
        "max_absolute_error": maximum_error,
        "mean_absolute_error": float(np.mean(errors)),
        "passed": maximum_error <= 1e-6,
    }


def eligible_exposure(patient: Any, last_visit_day: float) -> float:
    if not patient.true_recurrence_event or patient.true_recurrence_day is None:
        return 0.0
    ends = [last_visit_day, float(patient.true_recurrence_day)]
    if patient.competing_event_day is not None:
        ends.append(float(patient.competing_event_day))
    if patient.administrative_censor_day is not None:
        ends.append(float(patient.administrative_censor_day))
    return max(0.0, min(ends))


def render_report(result: dict[str, Any]) -> str:
    g1 = result["g1_transition_check"]
    g2 = result["g2_poisson_check"]
    lines = [
        "# EXP-CORE-ML-011: simulator mechanism validation",
        "",
        "> Synthetic mechanism checks only; these results do not establish clinical calibration or biological realism.",
        "",
        f"Study source commit: `{result['source_commit']}`. Profile: `{result['profile_id']}`.",
        "",
        "## G1 first-order secretion and clearance",
        "",
        f"Independent RK4 cases: {g1['cases']}; maximum absolute error: {g1['max_absolute_error']:.12g}; passed: {g1['passed']}; recurrence-free signal violations: {g1['no_recurrence_signal_violations']}.",
        "",
        "## G2 Poisson shot noise",
        "",
        f"Patients: {g2['patients']}; observed recurrence-linked events: {g2['observed_events']}; expected events from eligible person-time: {g2['expected_events']:.6f}.",
        f"Exact Poisson p-value: {g2['poisson_p_value']:.8g}; conditional event-time uniform KS statistic: {g2['uniform_ks_statistic']:.8g}; p-value: {g2['uniform_ks_p_value']:.8g}.",
        f"No-recurrence event-count violations: {g2['no_recurrence_violations']}; event-count reconstruction mismatches: {g2['count_mismatches']}.",
        "",
        "## Replicates",
        "",
        "| generator | replicate | patients | recurrence-linked events | eligible person-days |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result["replicates"]:
        lines.append(
            f"| {row['generator']} | {row['replicate']} | {row['patients']} | {row['events']} | {row['eligible_person_days']:.3f} |"
        )
    lines += ["", "## Limits", "", result["limits"], ""]
    return "\n".join(lines)


def run() -> int:
    if any(path.exists() for path in OUTPUTS):
        raise SystemExit(
            "refused: registered output or access log already exists; do not rerun these seeds"
        )
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    if status.strip():
        raise SystemExit("refused: worktree must be clean before the registered run")
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    provenance = {
        "source_commit": source_commit,
        "runner_sha256": sha256_file(Path(__file__)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "simulator_sha256": sha256_file(ROOT / "packages/vigil-sim/vigil_sim/generators.py"),
        "mechanisms_sha256": sha256_file(ROOT / "packages/vigil-sim/vigil_sim/mechanisms.py"),
        "profile_sha256": sha256_file(PROFILE_PATH),
        "lock_sha256": sha256_file(LOCK_PATH),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "profile_id": profile["profile_id"],
        "status": "RUNNING",
    }
    (HERE / "ACCESS_LOG.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    try:
        mechanics = profile["generator_mechanics"]
        g1 = validate_g1_transitions(BASE_SEED)
        replicate_rows: list[dict[str, Any]] = []
        observed_total = 0
        expected_total = 0.0
        normalized_event_times: list[float] = []
        g1_no_recurrence_violations = 0
        no_recurrence_violations = 0
        count_mismatches = 0
        total_patients = 0
        for generator_name, offset in (("G1", 100000), ("G2", 200000)):
            generator_type = (
                GeneratorType.G1_SMOOTH if generator_name == "G1" else GeneratorType.G2_BURST
            )
            for replicate in range(REPLICATES):
                seed = BASE_SEED + offset + replicate * 10_000
                generator = get_generator(generator_type, seed=seed, population_config=profile)
                cohort = generator.generate_cohort(
                    num_patients=COHORT_SIZE, duration_days=DURATION_DAYS
                )
                latent_by_patient: dict[str, list[Any]] = {}
                for latent in cohort.latent_states:
                    latent_by_patient.setdefault(latent.patient_id, []).append(latent)
                row_events = 0
                row_exposure = 0.0
                for patient in cohort.patients:
                    states = latent_by_patient.get(patient.patient_id, [])
                    last_visit = max((state.day for state in states), default=0.0)
                    if generator_name == "G1" and not patient.true_recurrence_event:
                        if any(
                            state.m_ca153 != 0.0
                            or state.m_cea != 0.0
                            or state.b_loc
                            + state.b_bone
                            + state.b_liver
                            + state.b_lung
                            + state.b_brain
                            != 0.0
                            for state in states
                        ):
                            g1_no_recurrence_violations += 1
                    if generator_name == "G2":
                        exposure = eligible_exposure(patient, last_visit)
                        row_exposure += exposure
                        event_count = states[-1].mechanism_event_count if states else 0
                        row_events += event_count
                        if not patient.true_recurrence_event and event_count != 0:
                            no_recurrence_violations += 1
                        rng = patient_rng(seed, patient.patient_id, "g2-event-times")
                        event_times = draw_poisson_event_times(
                            exposure,
                            mechanics["g2"]["shot_noise"]["event_rate_per_day"],
                            rng,
                        )
                        if event_times.size != event_count:
                            count_mismatches += 1
                        if exposure > 0:
                            normalized_event_times.extend((event_times / exposure).tolist())
                total_patients += len(cohort.patients)
                if generator_name == "G2":
                    observed_total += row_events
                    expected_total += (
                        mechanics["g2"]["shot_noise"]["event_rate_per_day"] * row_exposure
                    )
                replicate_rows.append(
                    {
                        "generator": generator_name,
                        "replicate": replicate,
                        "seed": seed,
                        "patients": len(cohort.patients),
                        "events": row_events,
                        "eligible_person_days": row_exposure,
                    }
                )
        poisson_p = poisson_two_sided_exact(observed_total, expected_total)
        uniform_ks = kstest(normalized_event_times, "uniform") if normalized_event_times else None
        g2 = {
            "patients": total_patients // 2,
            "observed_events": observed_total,
            "expected_events": expected_total,
            "poisson_p_value": poisson_p,
            "uniform_ks_statistic": float(uniform_ks.statistic) if uniform_ks else 0.0,
            "uniform_ks_p_value": float(uniform_ks.pvalue) if uniform_ks else 0.0,
            "uniform_event_positions": len(normalized_event_times),
            "no_recurrence_violations": no_recurrence_violations,
            "count_mismatches": count_mismatches,
        }
        g1["no_recurrence_signal_violations"] = g1_no_recurrence_violations
        passed = bool(
            g1["passed"]
            and g1_no_recurrence_violations == 0
            and poisson_p >= 0.01
            and uniform_ks is not None
            and float(uniform_ks.pvalue) >= 0.01
            and no_recurrence_violations == 0
            and count_mismatches == 0
        )
        result: dict[str, Any] = {
            **provenance,
            "status": "PASS" if passed else "FAIL",
            "g1_transition_check": g1,
            "g2_poisson_check": g2,
            "replicates": replicate_rows,
            "limits": "Synthetic mechanism fidelity only; no human parameter calibration, clinical validity, or real-cohort performance is established.",
        }
        result_path = HERE / "results.json"
        result_path.write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        report_text = render_report(result)
        (HERE / "REPORT.md").write_text(report_text, encoding="utf-8")
        if (HERE / "REPORT.md").read_text(encoding="utf-8") != render_report(
            json.loads(result_path.read_text(encoding="utf-8"))
        ):
            raise RuntimeError("saved-JSON report parity failed")
        provenance["status"] = result["status"]
        provenance["results_sha256"] = sha256_file(result_path)
        provenance["report_sha256"] = sha256_file(HERE / "REPORT.md")
        (HERE / "ACCESS_LOG.json").write_text(
            json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
        )
        print(f"EXP-CORE-ML-011 {result['status']}")
        return 0 if passed else 1
    except Exception as exc:
        provenance["status"] = "FAILED_DURING_RUN"
        provenance["failure"] = f"{type(exc).__name__}: {exc}"
        (HERE / "ACCESS_LOG.json").write_text(
            json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
        )
        raise


if __name__ == "__main__":
    raise SystemExit(run())
