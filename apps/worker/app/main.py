"""Worker entrypoint for ESG MVP asynchronous jobs.

The Phase 5 worker polls ``async_jobs`` for peer report parse jobs and runs the
mock parser pipeline.  It records all state in PostgreSQL so the API can expose
job progress without relying on an in-memory process queue.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.jobs.parse_peer_report import mark_job_failed, process_peer_report_parse_job

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://esg_user:esg_password@localhost:5432/esg_dev")
POLL_INTERVAL_SECONDS = float(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "5"))
RUN_ONCE = os.getenv("WORKER_RUN_ONCE", "false").lower() in {"1", "true", "yes"}
PARAM_PATTERN = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")
JSON_PARAM_KEYS = {"request_payload", "result_payload", "error_payload"}


class PsycopgDbAdapter:
    """Small adapter that lets job code use SQLAlchemy-style named params."""

    def __init__(self, cursor: psycopg.Cursor[dict[str, Any]]):
        self.cursor = cursor

    def execute(self, statement: str, params: dict[str, Any] | None = None) -> psycopg.Cursor[dict[str, Any]]:
        converted_params = {
            key: Jsonb(value) if key in JSON_PARAM_KEYS and isinstance(value, dict) else value
            for key, value in (params or {}).items()
        }
        converted_statement = PARAM_PATTERN.sub(r"%(\1)s", statement)
        return self.cursor.execute(converted_statement, converted_params)


def fetch_next_peer_report_job(cursor: psycopg.Cursor[dict[str, Any]]) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT job_id::text, tenant_id::text, enterprise_id::text, project_id::text,
               target_object_type, target_object_id::text, request_payload
        FROM async_jobs
        WHERE job_type='peer_report_parse'
          AND job_status IN ('pending', 'retrying')
        ORDER BY created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """
    )
    return cursor.fetchone()


def process_one_job() -> bool:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.transaction():
            with conn.cursor() as cursor:
                job = fetch_next_peer_report_job(cursor)
                if not job:
                    return False
                adapter = PsycopgDbAdapter(cursor)
                try:
                    process_peer_report_parse_job(adapter, job)
                except Exception as exc:  # noqa: BLE001 - worker must persist job failure details before continuing.
                    mark_job_failed(
                        adapter,
                        tenant_id=str(job["tenant_id"]),
                        job_id=str(job["job_id"]),
                        project_id=str(job["project_id"]),
                        peer_report_id=str(job["target_object_id"]),
                        error_code="PEER_REPORT_PARSE_FAILED",
                        message=exc.__class__.__name__,
                    )
                return True


def main() -> None:
    print("[worker] starting ESG worker for peer_report_parse jobs")
    while True:
        processed = process_one_job()
        if RUN_ONCE:
            return
        if not processed:
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
