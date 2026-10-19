#!/usr/bin/env bash
# import-linter needs all root_packages on PYTHONPATH (G-05 / ADR-0030).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/packages/vigil-core:${ROOT}/packages/vigil-eval:${ROOT}/packages/vigil-ml:${ROOT}/packages/vigil-sim:${ROOT}/packages/contracts:${ROOT}/apps/api${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
exec uv run lint-imports "$@"
