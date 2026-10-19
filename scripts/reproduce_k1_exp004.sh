#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

uv run --locked python scripts/train_k1_amortized.py
uv run --locked python experiments/EXP-K1-004/run.py --smoke
uv run --locked python experiments/EXP-K1-004/run.py
