#!/usr/bin/env bash
set -euo pipefail

DB_URL=${DATABASE_URL:-postgresql://esg_user:esg_password@localhost:5432/esg_dev}
DB_URL=${DB_URL/postgresql+psycopg:/postgresql:}

if [ -f "db/seed/ESG_PostgreSQL_Seed_Data_v0.1.sql" ]; then
  echo "Applying seed data..."
  psql "$DB_URL" -f db/seed/ESG_PostgreSQL_Seed_Data_v0.1.sql
else
  echo "No seed file found. Skipping."
fi
