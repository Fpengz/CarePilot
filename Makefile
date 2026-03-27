.PHONY: help dev test test-backend test-web lint typecheck clean install

CLI := uv run python scripts/cli.py

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies for backend and frontend
	uv sync
	cd apps/web && pnpm install

dev: ## Start all development services
	$(CLI) dev

test: ## Run comprehensive validation suite
	$(CLI) test comprehensive

test-backend: ## Run backend tests only
	$(CLI) test backend

test-web: ## Run web tests only
	$(CLI) test web

lint: ## Run backend and frontend linting
	uv run ruff check .
	cd apps/web && pnpm lint

typecheck: ## Run backend and frontend typechecking
	uv run ty check . --extra-search-path src --output-format concise
	cd apps/web && pnpm typecheck

clean: ## Remove build artifacts and caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache .ty_cache
	rm -rf apps/web/.next apps/web/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
