BACKEND := uv run --directory backend

.PHONY: help install db-up db-down migrate migration run lint format typecheck test test-int test-all

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install backend dependencies
	cd backend && uv sync

db-up: ## Start PostgreSQL
	docker compose up -d --wait db

db-down: ## Stop PostgreSQL
	docker compose stop db

migrate: ## Apply migrations to the dev database
	$(BACKEND) alembic upgrade head

migration: ## Generate a migration from the models: make migration m="description"
	$(BACKEND) alembic revision --autogenerate -m "$(m)"

run: ## Start the API with auto-reload
	$(BACKEND) uvicorn app.main:app --reload

lint: ## Check code style
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .

format: ## Fix code style
	$(BACKEND) ruff check --fix .
	$(BACKEND) ruff format .

typecheck: ## Check types
	$(BACKEND) mypy

test: ## Unit tests (no database, no LLM)
	$(BACKEND) pytest -m "not integration and not llm"

test-int: db-up ## Integration tests (PostgreSQL)
	$(BACKEND) pytest -m integration

test-all: db-up ## All tests except LLM, with coverage
	$(BACKEND) pytest -m "not llm" --cov
