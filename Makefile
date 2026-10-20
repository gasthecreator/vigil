# Vigil Precision Oncology Platform Makefile
# Reference: docs/MASTER_PLAN.md §9.1, §12, §14

.PHONY: help setup fmt lint test verify-phase reproduce reproduce-ml reproduce-ml-core reproduce-ml-core-cross-generator reproduce-ml-core-feature-rerun reproduce-ml-core-complete-rerun run-k7-002 verify-k7-002 typecheck coverage-ratchet import-lint docs-build docs-check api-dev web-dev demo status clean

PYTHON ?= python3
UV ?= uv

help:
	@echo "Vigil Precision Oncology Surveillance Platform"
	@echo "------------------------------------------------"
	@echo "make setup              Install workspace dependencies (uv + npm)"
	@echo "make fmt                Format Python code with ruff"
	@echo "make lint               Run linters (ruff, claims-check, web lint)"
	@echo "make typecheck          mypy --strict (ADR-0030 scope) + import-linter"
	@echo "make coverage-ratchet   Measure core+eval coverage and enforce floor"
	@echo "make test               Run unit, property, and integration tests"
	@echo "make verify-phase       Verify phase exit gates (e.g. make verify-phase PHASE=0)"
	@echo "make reproduce          Verify study evidence, derived reports, and supply-chain outputs (G-11)"
	@echo "make reproduce-ml       Reproduce Phase 2 ML benchmarks (studies S1, S3, S9)"
	@echo "make reproduce-ml-core  Run preregistered single-generator core model tuning study"
	@echo "make reproduce-ml-core-cross-generator  Run preregistered G1/G2 to G3 robustness study"
	@echo "make reproduce-ml-core-feature-rerun  Run corrected-feature baseline re-evaluation"
	@echo "make reproduce-ml-core-complete-rerun  Run full preregistered baseline contrasts"
	@echo "make run-k7-002        Execute the one-time preregistered K7 synthetic study"
	@echo "make verify-k7-002     Verify committed K7 replacement artifacts without cohort regeneration"
	@echo "make docs-build         Build MkDocs Material site into site/"
	@echo "make docs-check         Build docs + check_docs_links + README version claims"
	@echo "make api-dev            Run FastAPI backend in reload mode"
	@echo "make web-dev            Run Next.js clinician workstation"
	@echo "make demo               Seed synthetic DB + API + web (owner script in docs/demo/)"
	@echo "make status             Regenerate docs/STATUS.md from ledger/hazards/stubs/CI"
	@echo "make compose-up         docker compose -f infra/docker-compose.yml up --build"
	@echo "make scale-postgres     Run Postgres scale probe (writes reports/perf/SCALE_TEST_RESULTS.json)"
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

typecheck:
	@echo "==> mypy --strict (vigil-core, vigil-eval, m5.py)..."
	$(UV) run mypy --config-file pyproject.toml
	@echo "==> import-linter contracts..."
	bash scripts/run_lint_imports.sh

coverage-ratchet:
	@mkdir -p reports/quality
	$(UV) run pytest packages/vigil-core/tests packages/vigil-eval/tests \
		--cov=vigil_core --cov=vigil_eval \
		--cov-report=json:reports/quality/coverage-run.json -q
	$(UV) run python scripts/check_coverage_ratchet.py --coverage-json reports/quality/coverage-run.json

import-lint:
	bash scripts/run_lint_imports.sh

docs-build:
	$(UV) sync --group docs
	$(UV) run --group docs mkdocs build --config-file mkdocs.yml

docs-check: docs-build
	$(PYTHON) scripts/check_docs_links.py
	$(UV) run python scripts/check_readme_version_claims.py

reproduce:
	@echo "==> Regenerating/verifying committed reports (G-11)..."
	$(UV) run python scripts/reproduce.py

reproduce-ml:
	@echo "==> Reproducing VigilBench Phase 2 Classical Core Benchmarks..."
	$(UV) run python scripts/run_benchmarks.py

reproduce-ml-core:
	@echo "==> EXP-CORE-ML-003 is historical and stale; its runner fails closed."
	$(UV) run python experiments/EXP-CORE-ML-003/run.py

reproduce-ml-core-cross-generator:
	@echo "==> EXP-CORE-ML-004 is historical and stale; its runner fails closed."
	$(UV) run python experiments/EXP-CORE-ML-004/run.py

reproduce-ml-core-feature-rerun:
	@echo "==> EXP-CORE-ML-007 is exploratory and already ran; its runner fails closed on replay."
	$(UV) run python experiments/EXP-CORE-ML-007/run.py

reproduce-ml-core-complete-rerun:
	@echo "==> Running preregistered complete paired-contrast core-model evaluation..."
	$(UV) run python experiments/EXP-CORE-ML-008/run.py

run-k7-002:
	$(UV) run python experiments/EXP-S8-K7-002/run.py

verify-k7-002:
	$(UV) run python experiments/EXP-S8-K7-002/verify.py

api-dev:
	$(UV) run uvicorn vigil_api.main:app --host 0.0.0.0 --port 8000 --reload

web-dev:
	npm --prefix apps/web run dev

demo:
	@echo "==> Synthetic demo (research prototype; synthetic=true on all seed rows)"
	$(UV) run python scripts/run_demo.py

status:
	$(UV) run python scripts/generate_status.py

compose-up:
	docker compose -f infra/docker-compose.yml --env-file infra/.env.compose up --build

scale-postgres:
	@if [ -z "$$DATABASE_URL" ] || echo "$$DATABASE_URL" | grep -q '^sqlite'; then \
		echo "Set DATABASE_URL=postgresql+psycopg://... first"; exit 2; \
	fi
	$(UV) run python scripts/run_scale_test_postgres.py

clean:
	rm -rf .pytest_cache .ruff_cache dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
