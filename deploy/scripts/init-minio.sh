#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required"
  exit 1
fi

echo "Creating MinIO buckets through container client..."
docker run --rm --network host minio/mc sh -c '
  mc alias set local http://localhost:9000 minioadmin minioadmin &&
  mc mb -p local/esg-files || true &&
  mc mb -p local/esg-exports || true &&
  mc mb -p local/esg-temp || true
'
