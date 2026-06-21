#!/usr/bin/env bash
set -euo pipefail

echo "[secret-scan] Checking obvious secrets"

if git ls-files | grep -E '(^|/)\.env$|\.env\.local$|\.env\.prod$|\.pem$|\.key$|id_rsa' >/dev/null; then
  echo "[secret-scan] Forbidden secret-like file is tracked"
  git ls-files | grep -E '(^|/)\.env$|\.env\.local$|\.env\.prod$|\.pem$|\.key$|id_rsa'
  exit 1
fi

PATTERN='(OPENAI_API_KEY|AI_API_KEY|AWS_SECRET_ACCESS_KEY|SECRET_KEY|JWT_SECRET|PASSWORD=|PRIVATE KEY|sk-[A-Za-z0-9_-]{20,})'
if git grep -n -E "$PATTERN" -- . ':!*.md' ':!scripts/check-no-secrets.sh' ':!.env.example' >/tmp/secret_scan_hits.txt; then
  echo "[secret-scan] Potential secret found:"
  cat /tmp/secret_scan_hits.txt
  exit 1
fi

echo "[secret-scan] OK"
