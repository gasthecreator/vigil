"""Deterministically render the registered M3 sensitivity report from saved JSON."""

from __future__ import annotations

from typing import Any


def _format_auc(value: float | None) -> str:
    return "undefined" if value is None else f"{value:.4f}"


def render_report(data: dict[str, Any]) -> str:
    lines = [
        f"# {data['study_id']}: M3 synthetic-assumption sensitivity audit",
        "",
        "> Synthetic robustness only. This study does not select parameters, validate clinical performance, or establish a patient-level probability.",
        "",
        f"Protocol: `{data['protocol_version']}`  ",
        f"Source commit: `{data['source_commit']}`  ",
        f"Input strata: {len(data['strata'])}  ",
        f"Configurations: {len(data['configurations'])}",
        "",
        "M3 scores are conditional on synthetic assumptions. Descriptive AUROCs compare those scores with simulator labels whose semantics do not equal M3's components; they are not performance evidence.",
        "",
        "## Input eligibility and exclusions",
        "",
        "| Generator | Seed | Eligible evaluations | Unobserved | Missing values | Nonfinite values | Nonpositive values | Nonfinite days |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for stratum in data["strata"]:
        lines.append(
            f"| {stratum['generator']} | {stratum['seed']} | {stratum['n_evaluations']} | "
            f"{stratum['excluded_unobserved_observations']} | {stratum['excluded_missing_values']} | "
            f"{stratum['excluded_nonfinite_values']} | {stratum['excluded_nonpositive_values']} | "
            f"{stratum['excluded_nonfinite_days']} |"
        )
    lines.extend(
        [
            "",
            "## Paired sensitivity by stratum",
            "",
            "| Configuration | Generator | Seed | Evaluations | Invalid | Abstentions | Median absolute score delta | P95 absolute score delta | Action switch rate | AUROC vs recurrence label* | AUROC vs injected-error label* | Action counts |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for config in data["configurations"]:
        for cell in config["strata"]:
            recurrence_auc = cell["descriptive_auc_recurrence"]
            error_auc = cell["descriptive_auc_injected_error"]
            counts = ", ".join(f"{key}={value}" for key, value in sorted(cell["action_counts"].items()))
            lines.append(
                f"| `{config['config_id']}` | {cell['generator']} | {cell['seed']} | {cell['n_evaluations']} | "
                f"{cell['invalid_count']} | {cell['abstention_count']} | "
                f"{cell['median_absolute_score_delta']:.6f} | {cell['p95_absolute_score_delta']:.6f} | "
                f"{cell['action_switch_rate']:.4f} | {_format_auc(recurrence_auc)} | {_format_auc(error_auc)} | {counts} |"
            )
    lines.extend(
        [
            "",
            "\\* Descriptive synthetic-label comparisons only; no patient-level confidence intervals or clinical interpretation are registered.",
            "",
            "## Integrity",
            "",
            "Each stratum records separate hashes for model inputs and analysis-only labels. Every configuration uses the same input hashes. Source, simulator, config, preregistration, runner, renderer, lockfile, and repository revision hashes are in `ACCESS_LOG.json`.",
            "",
            "No configuration is ranked or selected. These results do not establish clinical plausibility for any assumption setting; M3 remains research-only.",
            "",
        ]
    )
    return "\n".join(lines)
