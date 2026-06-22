#!/usr/bin/env bash
set -euo pipefail

echo "[migration-check] Checking database scripts"

if [ ! -d db/ddl ]; then
  echo "db/ddl directory missing"
  exit 1
fi

if [ ! -d db/seed ]; then
  echo "db/seed directory missing"
  exit 1
fi

mkdir -p db/migrations

BAD_NAMES=$(find db/migrations -type f -name '*.sql' | grep -v -E '/V[0-9]{3}__.+\.sql$' || true)
if [ -n "$BAD_NAMES" ]; then
  echo "Migration files must match V001__description.sql naming pattern:"
  echo "$BAD_NAMES"
  exit 1
fi

echo "[migration-check] OK"
