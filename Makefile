# ── LOG Analyzer — Makefile ──────────────────────────────────
# Usage:
#   make lint           — ruff lint (backend)
#   make format         — auto-format with ruff (backend)
#   make typecheck      — mypy strict (backend)
#   make test           — pytest (backend)
#   make test-cov       — pytest with coverage (backend)
#   make docstrings     — interrogate docstring coverage
#   make security       — pip-audit + npm audit
#   make frontend-lint  — eslint (frontend)
#   make frontend-check — tsc + build (frontend)
#   make check          — backend lint + typecheck + test
#   make check-all      — full pre-push equivalent (both stacks)
#   make ci-local       — run GA workflow locally via act
#   make docker-up      — start Docker Compose
#   make docker-down    — stop Docker Compose
# ─────────────────────────────────────────────────────────────

.PHONY: lint format typecheck test test-cov docstrings security \
        frontend-lint frontend-check check check-all ci-local \
        docker-up docker-down clean hooks

# ── Python: Linting & Formatting ─────────────────────────────

lint:
	cd backend && uv run ruff check src/ tests/

format:
	cd backend && uv run ruff format src/ tests/

typecheck:
	cd backend && uv run mypy src/

# ── Python: Testing ──────────────────────────────────────────

test:
	cd backend && uv run pytest tests/ -v

test-cov:
	cd backend && uv run pytest tests/ --cov=src/log_analyzer --cov-report=term-missing

# ── Python: Docstring Coverage ───────────────────────────────

docstrings:
	cd backend && uv run interrogate -c pyproject.toml src/

# ── Security Audits ──────────────────────────────────────────

security:
	@echo "── pip-audit (Python) ──"
	cd backend && uv run pip-audit || true
	@echo ""
	@echo "── npm audit (Frontend) ──"
	cd frontend && npm audit --audit-level=moderate || true

# ── Frontend ─────────────────────────────────────────────────

frontend-lint:
	cd frontend && npx eslint . --max-warnings=0

frontend-check: frontend-lint
	cd frontend && npx tsc --noEmit
	cd frontend && npm run build

# ── Combined Checks ──────────────────────────────────────────

check: lint typecheck test
	@echo "✅ Backend checks passed"

check-all: lint typecheck test docstrings security frontend-check
	@echo ""
	@echo "✅ All checks passed (pre-push equivalent)"

# ── CI Local (act) ───────────────────────────────────────────

ci-local:
	act push --container-architecture linux/amd64 --action-offline-mode

# ── Hooks Setup ──────────────────────────────────────────────

hooks:
	uv run pre-commit install
	uv run pre-commit install --hook-type pre-push
	@echo "✅ pre-commit and pre-push hooks installed"

# ── Run ──────────────────────────────────────────────────────

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

# ── Cleanup ──────────────────────────────────────────────────

clean:
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
