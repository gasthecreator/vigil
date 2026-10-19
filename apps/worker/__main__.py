"""Thin worker entrypoint (G-12 / ADR-0031).

Delegates to ``vigil_api.worker`` so the planned ``apps/worker`` layout exists
without duplicating the outbox poller. Prefer:

  python -m apps.worker
  # or, from PYTHONPATH that includes apps/:
  python -m worker
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Ensure the API package is importable when invoked as ``python -m worker`` from repo root.
_API = Path(__file__).resolve().parents[1] / "api"
if str(_API) not in sys.path:
    sys.path.insert(0, str(_API))

if __name__ == "__main__":
    sys.argv[0] = "vigil_api.worker"
    runpy.run_module("vigil_api.worker", run_name="__main__", alter_sys=True)
