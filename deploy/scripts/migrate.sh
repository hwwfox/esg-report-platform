#!/usr/bin/env bash
set -euo pipefail

DB_URL=${DATABASE_URL:-postgresql://esg_user:esg_password@localhost:5432/esg_dev}
# psycopg SQLAlchemy URL contains +psycopg; psql expects normal PostgreSQL URL.
DB_URL=${DB_URL/postgresql+psycopg:/postgresql:}

if [ -f "db/ddl/ESG_PostgreSQL_DDL_v0.1.sql" ]; then
  echo "Applying initial DDL..."
  psql "$DB_URL" -f db/ddl/ESG_PostgreSQL_DDL_v0.1.sql
else
  echo "No DDL file found. Skipping."
fi
if [ -d "db/migrations" ]; then
  while IFS= read -r migration; do
    echo "Applying migration ${migration}..."
    psql "$DB_URL" -f "$migration"
  done < <(find db/migrations -maxdepth 1 -type f -name 'V[0-9][0-9][0-9]__*.sql' | sort)
fi
