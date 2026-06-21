SHELL := /bin/bash

.PHONY: help install dev-up dev-down storage-init migrate seed db-reset api worker ai-gateway web lint typecheck test test-api test-e2e openapi-check schema-check docker-build clean

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
	@if [ -f apps/web/package.json ]; then cd apps/web && pnpm install; fi
	@if [ -f apps/api/requirements.txt ]; then python -m pip install -r apps/api/requirements.txt; fi
	@if [ -f apps/worker/requirements.txt ]; then python -m pip install -r apps/worker/requirements.txt; fi
	@if [ -f apps/ai-gateway/requirements.txt ]; then python -m pip install -r apps/ai-gateway/requirements.txt; fi

dev-up:
	docker compose -f docker-compose.dev.yml up -d postgres redis minio mailhog

dev-down:
	docker compose -f docker-compose.dev.yml down

storage-init:
	bash deploy/scripts/init-minio.sh

migrate:
	bash deploy/scripts/migrate.sh

seed:
	bash deploy/scripts/seed.sh

db-reset:
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
	cd apps/web && pnpm dev --host 0.0.0.0 --port 3000

lint:
	@echo "TODO: add ruff/eslint checks once dependencies are finalized"

typecheck:
	@if [ -f apps/web/package.json ]; then cd apps/web && pnpm typecheck; fi

test:
	pytest apps/api/tests apps/worker/tests apps/ai-gateway/tests || true

test-api:
	pytest apps/api/tests || true

test-e2e:
	@if [ -f apps/web/package.json ]; then cd apps/web && pnpm test:e2e; fi

openapi-check:
	python tools/codegen/check_openapi.py contracts/openapi/ESG_P0_OpenAPI_v0.1.yaml

schema-check:
	python tools/codegen/check_json_schemas.py contracts/schemas ai/schemas

docker-build:
	@echo "TODO: add service Docker builds after first implementation"

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
