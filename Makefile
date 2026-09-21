.PHONY: help api web test lint fmt typecheck up down kind-up kind-down

help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | cut -d: -f1 | sort

api:
	cd backend && uv run uvicorn interview_agent.api.app:app --reload --port 8000

web:
	cd web && pnpm dev

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .

fmt:
	cd backend && uv run ruff format . && uv run ruff check --fix .

typecheck:
	cd backend && uv run mypy src

up:
	docker compose -f infra/compose/docker-compose.yml up -d

down:
	docker compose -f infra/compose/docker-compose.yml down

kind-up:
	kind create cluster --config infra/kind/kind-config.yaml --name interview-agent

kind-down:
	kind delete cluster --name interview-agent
