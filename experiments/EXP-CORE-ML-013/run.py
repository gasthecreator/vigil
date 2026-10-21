#!/usr/bin/env python3
"""One-time registered v4 synthetic mechanism implementation audit."""

from __future__ import annotations

import hashlib
import json
import math
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
from vigil_sim.mechanisms import draw_patient_shot_noise_trace  # noqa: E402

EXP = Path(__file__).resolve().parent
PROFILE = ROOT / "packages/vigil-sim/vigil_sim/config/synthetic_population_core_v4.json"
BASE_SEED = 20270101
REPLICATES = range(5)
COHORT_SIZE = 1000
DURATION_DAYS = 730.0
STREAM_OFFSETS = {"G1": 310000, "G2": 420000, "G3": 530000}
STREAM_NAMES = {"event_times": "g2-event-times", "event_amplitudes": "g2-event-amplitudes"}
ALPHA = 0.01


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cohort_seed(stream: str, replicate: int) -> int:
    return BASE_SEED + STREAM_OFFSETS[stream] + 20_000 * replicate


def patient_exposure(patient: Any, latent_states: list[Any]) -> float:
    end_day = max((float(state.day) for state in latent_states), default=0.0)
    terminal_days = [end_day]
    if patient.true_recurrence_event and patient.true_recurrence_day is not None:
        terminal_days.append(max(0.0, float(patient.true_recurrence_day)))
    else:
        terminal_days.append(0.0)
    if patient.competing_event_day is not None:
        terminal_days.append(max(0.0, float(patient.competing_event_day)))
    if patient.administrative_censor_day is not None:
        terminal_days.append(max(0.0, float(patient.administrative_censor_day)))
    return min(terminal_days)


def exact_two_sided_poisson_p(observed: int, expected: float) -> float:
    """Probability-ordering exact two-sided Poisson test, including zero rate."""
    if observed < 0 or not np.isfinite(expected) or expected < 0.0:
        raise ValueError("Poisson observation and expectation must be non-negative")
    if expected == 0.0:
        return 1.0 if observed == 0 else 0.0
    observed_probability = float(poisson.pmf(observed, expected))
    upper = int(poisson.ppf(1.0 - 1e-14, expected))
    values = np.arange(upper + 1)
    probabilities = poisson.pmf(values, expected)
    return float(min(1.0, probabilities[probabilities <= observed_probability * (1.0 + 1e-12)].sum()))


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=p_values.__getitem__)
    adjusted: dict[str, float] = {}
    running_max = 0.0
    count = len(ordered)
    for rank, name in enumerate(ordered):
        running_max = max(running_max, (count - rank) * p_values[name])
        adjusted[name] = float(min(1.0, running_max))
    return adjusted


def finite_nonnegative(value: float, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise RuntimeError(f"{name} is not finite and non-negative: {result}")
    return result


def _g2_diagnostics(cohort: Any, shot: dict[str, float]) -> dict[str, Any]:
    latent_by_patient: dict[str, list[Any]] = {}
    for state in cohort.latent_states:
        latent_by_patient.setdefault(state.patient_id, []).append(state)

    recurrent_counts: list[int] = []
    normalized_event_times: list[float] = []
    amplitudes: list[float] = []
    eligible_person_time = 0.0
    eligible_count = 0
    exclusions: dict[str, int] = {"not_true_recurrence": 0, "missing_recurrence_day": 0, "zero_exposure": 0}

    for patient in cohort.patients:
        states = latent_by_patient.get(patient.patient_id, [])
        exposure = patient_exposure(patient, states)
        if not patient.true_recurrence_event:
            exclusions["not_true_recurrence"] += 1
            if states and any(
                state.mechanism_event_count != 0 or state.m_ca153 != 0.0 or state.m_cea != 0.0
                for state in states
            ):
                raise RuntimeError("G2 recurrence-free control has event count or marker signal")
            continue
        if patient.true_recurrence_day is None:
            exclusions["missing_recurrence_day"] += 1
            continue
        if exposure <= 0.0:
            exclusions["zero_exposure"] += 1
            continue

        event_times, event_amplitudes = draw_patient_shot_noise_trace(
            cohort.seed,
            patient.patient_id,
            exposure,
            shot["event_rate_per_day"],
            shot["burden_amplitude_mean"],
            shot["burden_amplitude_coefficient_of_variation"],
        )
        if not states or int(np.count_nonzero(event_times <= states[-1].day)) != states[-1].mechanism_event_count:
            raise RuntimeError(f"G2 regenerated trace count disagrees with production for {patient.patient_id}")
        if not np.isfinite(event_times).all() or np.any(event_times < 0.0) or np.any(event_times > exposure):
            raise RuntimeError(f"G2 event trace falls outside registered exposure for {patient.patient_id}")
        recurrent_counts.append(int(event_times.size))
        normalized_event_times.extend((event_times / exposure).tolist())
        amplitudes.extend(event_amplitudes.tolist())
        eligible_person_time += exposure
        eligible_count += 1

    rate = float(shot["event_rate_per_day"])
    expected = rate * eligible_person_time
    observed = int(sum(recurrent_counts))
    p_count = exact_two_sided_poisson_p(observed, expected)

    if normalized_event_times:
        time_ks = kstest(np.asarray(normalized_event_times), "uniform")
        time_statistic, p_time = float(time_ks.statistic), float(time_ks.pvalue)
    else:
        time_statistic, p_time = None, 1.0

    amplitude_array = np.asarray(amplitudes, dtype=float)
    cv = float(shot["burden_amplitude_coefficient_of_variation"])
    log_sigma = math.sqrt(math.log1p(cv**2))
    log_mu = math.log(float(shot["burden_amplitude_mean"])) - log_sigma**2 / 2.0
    if amplitude_array.size:
        amp_mean = float(amplitude_array.mean())
        amp_cv = float(amplitude_array.std(ddof=1) / amp_mean) if amplitude_array.size > 1 else 0.0
        standardized = (np.log(amplitude_array) - log_mu) / log_sigma
        amp_ks = kstest(standardized, "norm")
        amp_statistic, p_amplitude = float(amp_ks.statistic), float(amp_ks.pvalue)
    else:
        amp_mean, amp_cv, amp_statistic, p_amplitude = None, None, None, 1.0

    raw_p = {"poisson_count": p_count, "event_time_uniformity": p_time, "amplitude_lognormality": p_amplitude}
    adjusted = holm_adjust(raw_p)
    return {
        "n_true_recurrent": int(sum(bool(p.true_recurrence_event) for p in cohort.patients)),
        "n_eligible_recurrent": eligible_count,
        "n_excluded_true_recurrent": exclusions["missing_recurrence_day"] + exclusions["zero_exposure"],
        "exclusions": exclusions,
        "eligible_recurrence_person_time_days": finite_nonnegative(eligible_person_time, "eligible person-time"),
        "production_event_count_total": observed,
        "event_count_mean_per_eligible_recurrent_patient": float(np.mean(recurrent_counts)) if recurrent_counts else None,
        "event_count_variance_per_eligible_recurrent_patient": float(np.var(recurrent_counts, ddof=1)) if len(recurrent_counts) > 1 else None,
        "poisson_expected_count": finite_nonnegative(expected, "expected Poisson count"),
        "conditional_event_time_uniform_ks_statistic": time_statistic,
        "amplitude_mean": amp_mean,
        "amplitude_coefficient_of_variation": amp_cv,
        "amplitude_standardized_lognormal_ks_statistic": amp_statistic,
        "diagnostic_p_values": raw_p,
        "holm_adjusted_p_values": adjusted,
        "holm_alpha": ALPHA,
        "holm_reject": {name: value < ALPHA for name, value in adjusted.items()},
        "n_event_times_for_distribution_checks": len(normalized_event_times),
        "n_amplitudes_for_distribution_checks": int(amplitude_array.size),
    }


def one_replicate(replicate: int, profile: dict[str, Any]) -> dict[str, Any]:
    cohorts = {}
    for stream, generator_type in (
        ("G1", GeneratorType.G1_SMOOTH),
        ("G2", GeneratorType.G2_BURST),
        ("G3", GeneratorType.G3_NOISE),
    ):
        seed = cohort_seed(stream, replicate)
        cohorts[stream] = get_generator(
            generator_type, seed=seed, population_config=profile
        ).generate_cohort(num_patients=COHORT_SIZE, duration_days=DURATION_DAYS)

    g1 = cohorts["G1"]
    g1_recurrent = sum(bool(patient.true_recurrence_event) for patient in g1.patients)
    g1_latent: dict[str, list[Any]] = {}
    for state in g1.latent_states:
        g1_latent.setdefault(state.patient_id, []).append(state)
    for patient in g1.patients:
        if not patient.true_recurrence_event:
            for state in g1_latent.get(patient.patient_id, []):
                if any((state.b_loc, state.b_bone, state.b_liver, state.b_lung, state.b_brain, state.m_ca153, state.m_cea)):
                    raise RuntimeError("G1 recurrence-free control has recurrence-linked signal")

    g2 = cohorts["G2"]
    g2_mechanics = profile["generator_mechanics"]["g2"]["shot_noise"]
    return {
        "replicate": replicate,
        "cohort_seeds": {stream: cohort_seed(stream, replicate) for stream in cohorts},
        "duration_days": DURATION_DAYS,
        "cohort_contract": {
            stream: {
                "n_generated": len(cohort.patients),
                "n_true_recurrent": int(sum(bool(p.true_recurrence_event) for p in cohort.patients)),
            }
            for stream, cohort in cohorts.items()
        },
        "g1_recurrence_count": int(g1_recurrent),
        "g1_recurrence_free_control_count": int(len(g1.patients) - g1_recurrent),
        "g2": _g2_diagnostics(g2, g2_mechanics),
        "g3_role": "comparison_contract_control_only_no_mechanism_or_performance_claim",
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "# EXP-CORE-ML-013: v4 simulator call-path mechanism verification",
        "",
        "Synthetic mechanism implementation audit only; no calibration, predictive-performance, population, or clinical claim.",
        f"Source commit: `{result['source_commit']}`",
        "",
        "## G1 recurrence counts and G2 event-process diagnostics",
        "",
        "| Replicate | G1 true recurrences | G2 true recurrences | G2 eligible recurrences | G2 eligible person-time (days) | G2 events | Poisson p | Event-time KS p | Amplitude KS p |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["replicates"]:
        g2 = row["g2"]
        p = g2["diagnostic_p_values"]
        lines.append(
            f"| {row['replicate']} | {row['g1_recurrence_count']} | {g2['n_true_recurrent']} | {g2['n_eligible_recurrent']} | {g2['eligible_recurrence_person_time_days']:.3f} | {g2['production_event_count_total']} | {p['poisson_count']:.6g} | {p['event_time_uniformity']:.6g} | {p['amplitude_lognormality']:.6g} |"
        )
    lines += ["", "## Holm-adjusted diagnostics", ""]
    for row in result["replicates"]:
        g2 = row["g2"]
        lines.append(f"### Replicate {row['replicate']}")
        lines.append("")
        lines.append(
            f"- G2 event-count mean/variance per eligible recurrent patient: {g2['event_count_mean_per_eligible_recurrent_patient']} / {g2['event_count_variance_per_eligible_recurrent_patient']}."
        )
        lines.append(
            f"- Amplitude mean/CV: {g2['amplitude_mean']} / {g2['amplitude_coefficient_of_variation']}; standardized lognormal KS statistic: {g2['amplitude_standardized_lognormal_ks_statistic']}."
        )
        lines.append(f"- Exclusions: `{json.dumps(g2['exclusions'], sort_keys=True)}`.")
        lines.append(
            f"- Holm-adjusted p-values: `{json.dumps(g2['holm_adjusted_p_values'], sort_keys=True)}`; reject at alpha {ALPHA}: `{json.dumps(g2['holm_reject'], sort_keys=True)}`."
        )
        lines.append("")
    lines += [
        "G1 recurrence counts and G2 event counts are separate quantities. G3 is included only as a comparison/contract control; this study makes no G3 mechanism or performance claim. Per-replicate diagnostics, exclusions, and eligible person-time are preserved in `results.json`.",
        "",
        "All findings are limited to software fidelity under the frozen synthetic profile. They do not close profile calibration, verification bias, population realism, model performance, or clinical validation.",
        "",
    ]
    return "\n".join(lines)


def _access_record(commit: str) -> dict[str, Any]:
    generator_source = ROOT / "packages/vigil-sim/vigil_sim/generators.py"
    mechanisms_source = ROOT / "packages/vigil-sim/vigil_sim/mechanisms.py"
    return {
        "experiment_id": "EXP-CORE-ML-013",
        "source_commit": commit,
        "preregistration_sha256": sha(EXP / "PREREG.md"),
        "runner_sha256": sha(Path(__file__)),
        "generator_source_sha256": sha(generator_source),
        "mechanisms_source_sha256": sha(mechanisms_source),
        "profile_sha256": sha(PROFILE),
        "simulator_pyproject_sha256": sha(ROOT / "packages/vigil-sim/pyproject.toml"),
        "environment_lock_sha256": sha(ROOT / "uv.lock"),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "design": {
            "base_seed": BASE_SEED,
            "stream_offsets": STREAM_OFFSETS,
            "replicate_seed_increment": 20_000,
            "replicates": len(REPLICATES),
            "patients_per_generator_per_replicate": COHORT_SIZE,
            "duration_days": DURATION_DAYS,
            "patient_stream_names": STREAM_NAMES,
            "holm_family_alpha": ALPHA,
        },
        "completed": False,
    }


def write_saved_result_and_report(
    result_path: Path, report_path: Path, result: dict[str, Any]
) -> None:
    """Write results first, then render and byte-verify the report from saved JSON."""
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    saved_result = json.loads(result_path.read_text(encoding="utf-8"))
    rendered = render(saved_result)
    report_path.write_text(rendered, encoding="utf-8")
    parity_result = json.loads(result_path.read_text(encoding="utf-8"))
    if report_path.read_text(encoding="utf-8") != render(parity_result):
        raise RuntimeError("Saved REPORT.md differs from rendering saved results.json")


def main() -> None:
    output_paths = [EXP / name for name in ("ACCESS_LOG.json", "results.json", "REPORT.md")]
    if any(path.exists() for path in output_paths):
        raise RuntimeError("Refusing EXP-CORE-ML-013: an access/result/report artifact already exists")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if status:
        raise RuntimeError("Refusing EXP-CORE-ML-013 from a dirty working tree")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    access = _access_record(commit)
    access_path = output_paths[0]
    access_path.write_text(json.dumps(access, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        replicates = [one_replicate(rep, profile) for rep in REPLICATES]
        result = {
            "experiment_id": "EXP-CORE-ML-013",
            "source_commit": commit,
            "profile_id": profile["profile_id"],
            "design": access["design"],
            "replicates": replicates,
        }
        write_saved_result_and_report(output_paths[1], output_paths[2], result)
        access.update(
            {
                "completed": True,
                "results_sha256": sha(output_paths[1]),
                "report_sha256": sha(output_paths[2]),
            }
        )
    except Exception as exc:
        access["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        access_path.write_text(json.dumps(access, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
