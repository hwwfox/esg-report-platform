#!/usr/bin/env bash
set -euo pipefail

echo "[ci-local] Start local Sprint 0 quality gate"

make lint
make typecheck
make test
make test-api
make openapi-check
make schema-check
make migration-check
bash scripts/check-no-secrets.sh
bash scripts/check-openapi-mock-sync.sh

echo "[ci-local] Quality gate completed"
