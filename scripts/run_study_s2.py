#!/usr/bin/env python3
"""Study S2 is retracted; this entrypoint fails closed.

The former implementation reported calibration values that were hard-coded and
evaluated the already examined test cohort (seed 42). Its K2 validity claims
also rely on assumptions that have not been established. Keeping the retired
calibration and report-generation functions importable would make it too easy
to recreate the unsupported claims.

See ``docs/audits/QUALITY-RERUN-2026-10.md`` before designing a new,
preregistered study with an independent test cohort.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "Study S2 is retracted. Its calibration outputs were hard-coded and "
        "test seed 42 has been examined. See "
        "docs/audits/QUALITY-RERUN-2026-10.md before designing a fresh "
        "preregistered replication.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
