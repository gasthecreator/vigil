# Vigil Precision Oncology Platform Makefile
# Reference: docs/MASTER_PLAN.md §9.1, §12, §14

.PHONY: help setup fmt lint test verify-phase reproduce-ml api-dev web-dev clean

PYTHON ?= python3
UV ?= /Users/gsanni/.local/bin/uv

help:
	@echo "Vigil Precision Oncology Surveillance Platform"
	@echo "------------------------------------------------"
	@echo "make setup              Install workspace dependencies (uv + npm)"
	@echo "make fmt                Format Python code with ruff"
	@echo "make lint               Run linters (ruff, claims-check, web lint)"
	@echo "make test               Run unit, property, and integration tests"
	@echo "make verify-phase       Verify phase exit gates (e.g. make verify-phase PHASE=0)"
	@echo "make reproduce-ml       Reproduce Phase 2 ML benchmarks (studies S1, S3, S9)"
	@echo "make api-dev            Run FastAPI backend in reload mode"
	@echo "make web-dev            Run Next.js clinician workstation"
	@echo "make clean              Remove build artifacts, caches, and test state"

setup:
	@echo "==> Setting up Python uv workspace..."
	$(UV) sync --all-packages
	@echo "==> Setting up Web npm dependencies..."
	npm --prefix apps/web install

fmt:
	$(UV) run ruff format .

lint:
	@echo "==> Verifying claims policy..."
	$(PYTHON) scripts/check_claims.py
	@echo "==> Verifying evidence register and citations..."
	$(PYTHON) scripts/check_evidence.py
	@echo "==> Verifying reality audit..."
	$(PYTHON) scripts/reality_audit.py --require-stub-registry
	@echo "==> Running ruff linter..."
	$(UV) run ruff check .
	@echo "==> Running web linter..."
	npm --prefix apps/web run lint

test:
	@echo "==> Executing test suites across packages..."
	$(UV) run pytest -v

audit-evidence:
	python3 scripts/audit_excerpts.py

verify-phase:
	@if [ -z "$(PHASE)" ]; then \
		echo "Error: PHASE variable required. Usage: make verify-phase PHASE=0"; \
		exit 1; \
	fi
	$(PYTHON) scripts/verify_phase.py --phase $(PHASE)

reproduce-ml:
	@echo "==> Reproducing VigilBench Phase 2 Classical Core Benchmarks..."
	$(UV) run python scripts/run_benchmarks.py

api-dev:
	$(UV) run uvicorn vigil_api.main:app --host 0.0.0.0 --port 8000 --reload

web-dev:
	npm --prefix apps/web run dev

clean:
	rm -rf .pytest_cache .ruff_cache dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
