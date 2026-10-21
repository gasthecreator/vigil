#!/usr/bin/env python3
"""Retired historical leakage comparison; use a newly preregistered study."""


def run_comparison(seed: int = 42, V: int = 10) -> None:
    """Reject reruns so current code cannot overwrite the historical result."""
    del seed, V  # Retain the old call signature for a useful migration error.
    raise RuntimeError(
        "The historical leakage comparison is retired and cannot regenerate its report. "
        "Its output is under Q-7 evidence reconciliation; register a new experiment before "
        "any rerun. See docs/audits/CORE-ML-CLAIMS-INVENTORY-2026-10.md."
    )


if __name__ == "__main__":
    run_comparison()
