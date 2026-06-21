#!/usr/bin/env bash
set -euo pipefail

echo "[ci-local] Start local quality gate"

bash scripts/check-no-secrets.sh
bash scripts/check-openapi-mock-sync.sh
bash scripts/check-migrations.sh

if [ -f package.json ]; then
  if grep -q '"lint"' package.json; then npm run lint; else echo "[ci-local] lint skipped"; fi
  if grep -q '"typecheck"' package.json; then npm run typecheck; else echo "[ci-local] typecheck skipped"; fi
  if grep -q '"test"' package.json; then npm test; else echo "[ci-local] test skipped"; fi
else
  echo "[ci-local] package.json not found, root node checks skipped"
fi

echo "[ci-local] Quality gate completed"
