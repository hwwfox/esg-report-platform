SHELL := /bin/bash

.PHONY: help install check-docker dev-up dev-down storage-init migrate seed db-reset api worker ai-gateway web lint typecheck test test-api test-e2e openapi-check schema-check migration-check ci-local docker-build clean

help:
	@echo "ESG Report Platform commands"
	@echo "  make install          Install local dependencies"
	@echo "  make dev-up           Start PostgreSQL, Redis, MinIO, Mailhog"
	@echo "  make dev-down         Stop local dependencies"
	@echo "  make storage-init     Create MinIO buckets"
	@echo "  make migrate          Run database DDL/migrations"
	@echo "  make seed             Load seed data"
	@echo "  make api              Start FastAPI API"
	@echo "  make worker           Start worker"
	@echo "  make ai-gateway       Start mock AI gateway"
	@echo "  make web              Start frontend"
	@echo "  make test             Run available tests"

install:
	@if [ -f apps/web/package.json ]; then cd apps/web && if command -v pnpm >/dev/null 2>&1; then pnpm install; else npm install --no-package-lock; fi; fi
	@if [ -f apps/api/requirements.txt ]; then python -m pip install -r apps/api/requirements.txt; fi
	@if [ -f apps/worker/requirements.txt ]; then python -m pip install -r apps/worker/requirements.txt; fi
	@if [ -f apps/ai-gateway/requirements.txt ]; then python -m pip install -r apps/ai-gateway/requirements.txt; fi

check-docker:
	@command -v docker >/dev/null 2>&1 || { echo "Docker is required for this command. Install Docker or run this target in a Docker-enabled environment."; exit 127; }
	@docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required for this command. Install the docker compose plugin or run this target in a Docker Compose-enabled environment."; exit 127; }

dev-up: check-docker
	docker compose -f docker-compose.dev.yml up -d postgres redis minio mailhog

dev-down: check-docker
	docker compose -f docker-compose.dev.yml down

storage-init:
	bash deploy/scripts/init-minio.sh

migrate:
	bash deploy/scripts/migrate.sh

seed:
	bash deploy/scripts/seed.sh

db-reset: check-docker
	docker compose -f docker-compose.dev.yml down -v
	docker compose -f docker-compose.dev.yml up -d postgres redis minio mailhog
	@echo "Waiting for PostgreSQL..." && sleep 5
	bash deploy/scripts/migrate.sh
	bash deploy/scripts/seed.sh

api:
	cd apps/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

worker:
	cd apps/worker && python -m app.main

ai-gateway:
	cd apps/ai-gateway && uvicorn app.main:app --reload --host 0.0.0.0 --port 9002

web:
	cd apps/web && if command -v pnpm >/dev/null 2>&1; then pnpm dev --host 0.0.0.0 --port 3000; else npm run dev -- --host 0.0.0.0 --port 3000; fi

lint:
	@echo "[lint] Placeholder: no ruff/eslint configuration yet; command is safe for Sprint 0 bootstrap."

typecheck:
	@if [ -f apps/web/package.json ]; then cd apps/web && if command -v pnpm >/dev/null 2>&1; then pnpm typecheck; else npm install --no-package-lock && npm run typecheck; fi; fi

test:
	cd apps/api && python -m pytest tests
	cd apps/worker && python -m pytest tests
	cd apps/ai-gateway && python -m pytest tests

test-api:
	cd apps/api && python -m pytest tests

test-e2e:
	@if [ -f apps/web/package.json ]; then cd apps/web && if command -v pnpm >/dev/null 2>&1; then pnpm test:e2e; else npm run test:e2e; fi; fi

openapi-check:
	python tools/codegen/check_openapi.py contracts/openapi/ESG_P0_OpenAPI_v0.1.yaml

schema-check:
	python tools/codegen/check_json_schemas.py contracts/schemas ai/schemas

migration-check:
	bash scripts/check-migrations.sh

ci-local:
	bash scripts/ci-local.sh

docker-build:
	@echo "TODO: add service Docker builds after first implementation"

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
