#!/usr/bin/env bash
set -euo pipefail

echo "[openapi-check] Checking OpenAPI and Mock directories"

if [ ! -d contracts/openapi ]; then
  echo "contracts/openapi directory missing"
  exit 1
fi

OPENAPI_COUNT=$(find contracts/openapi -type f \( -name '*.yaml' -o -name '*.yml' -o -name '*.json' \) | wc -l | tr -d ' ')
if [ "$OPENAPI_COUNT" = "0" ]; then
  echo "No OpenAPI contract found under contracts/openapi"
  exit 1
fi

if [ ! -d contracts/mock-data ]; then
  echo "contracts/mock-data directory missing"
  exit 1
fi

echo "[openapi-check] Found $OPENAPI_COUNT OpenAPI contract file(s)"
echo "[openapi-check] OK"
