from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.projects.router import _authorize_project

router = APIRouter(prefix="/api/v1/projects", tags=["ESG数据"])


def create_esg_data_records_for_submission(db: Session, *, tenant_id: str, enterprise_id: str, project_id: str, task_id: str, submission_id: str) -> int:
    """Materialize approved submission items into tenant-scoped ESG data records."""
    db.execute(text("""
        DELETE FROM esg_data_records
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND source_submission_id=:submission_id
    """), {"tenant_id": tenant_id, "project_id": project_id, "submission_id": submission_id})
    result = db.execute(text("""
        INSERT INTO esg_data_records (
          tenant_id, enterprise_id, project_id, project_topic_id, project_topic_metric_id,
          topic_code, topic_name, metric_code, metric_name, data_type, value, text_value, unit,
          period, org_unit_id, org_unit_name, source_task_id, source_submission_id,
          source_submission_item_id, source_file_ids, review_status, report_reference_status
        )
        SELECT tsi.tenant_id, :enterprise_id, tsi.project_id, pt.project_topic_id, ptm.project_topic_metric_id,
               pt.topic_code, pt.topic_name, ptm.metric_code, ptm.metric_name, ptm.data_type,
               tsi.value, tsi.text_value, COALESCE(tsi.unit, ptm.unit), tsi.period,
               tsi.org_unit_id, COALESCE(pou.org_unit_name, ou.org_unit_name), :task_id,
               tsi.submission_id, tsi.submission_item_id, tsi.attachment_file_ids,
               'approved', 'not_referenced'
        FROM task_submission_items tsi
        JOIN task_submissions ts ON ts.tenant_id=tsi.tenant_id AND ts.submission_id=tsi.submission_id
        JOIN project_topic_metrics ptm ON ptm.tenant_id=tsi.tenant_id AND ptm.project_topic_metric_id=tsi.project_topic_metric_id
        JOIN project_topics pt ON pt.tenant_id=ptm.tenant_id AND pt.project_topic_id=ptm.project_topic_id
        LEFT JOIN project_org_units pou ON pou.project_org_unit_id=tsi.org_unit_id AND pou.tenant_id=tsi.tenant_id
        LEFT JOIN org_units ou ON ou.org_unit_id=tsi.org_unit_id AND ou.tenant_id=tsi.tenant_id
        WHERE tsi.tenant_id=:tenant_id AND tsi.project_id=:project_id AND tsi.submission_id=:submission_id
          AND ts.task_id=:task_id AND ts.task_status='approved'
          AND (tsi.value IS NOT NULL OR NULLIF(tsi.text_value, '') IS NOT NULL)
    """), {"tenant_id": tenant_id, "enterprise_id": enterprise_id, "project_id": project_id, "task_id": task_id, "submission_id": submission_id})
    return max(result.rowcount or 0, 0)


@router.get("/{project_id}/esg-data-records")
def list_esg_data_records(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read")), topic_code: str | None = None, metric_code: str | None = None, org_unit_id: str | None = None, period: str | None = None, data_type: str | None = None, source_task_id: str | None = None):
    _authorize_project(request, db, user, project_id)
    clauses = ["tenant_id=:tenant_id", "project_id=:project_id"]
    params = {"tenant_id": user["current_tenant_id"], "project_id": project_id}
    for key, value in {"topic_code": topic_code, "metric_code": metric_code, "org_unit_id": org_unit_id, "period": period, "data_type": data_type, "source_task_id": source_task_id}.items():
        if value:
            clauses.append(f"{key}=:{key}")
            params[key] = value
    rows = db.execute(text(f"""
        SELECT data_record_id::text, project_id::text, topic_code, topic_name, metric_code, metric_name,
               data_type::text, value, text_value, unit, period, org_unit_id::text, org_unit_name,
               source_task_id::text, source_submission_id::text, source_submission_item_id::text,
               source_file_ids, review_status::text, report_reference_status, created_at, updated_at
        FROM esg_data_records
        WHERE {' AND '.join(clauses)}
        ORDER BY topic_name, metric_name, period NULLS LAST, created_at DESC
    """), params).mappings().all()
    return ok({"items": [dict(row) for row in rows], "total": len(rows)}, request_id=request.state.request_id)


@router.get("/{project_id}/esg-data-records/{data_record_id}/sources")
def esg_data_record_sources(project_id: str, data_record_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_project(request, db, user, project_id)
    record = db.execute(text("""
        SELECT data_record_id::text, source_task_id::text, source_submission_id::text,
               source_submission_item_id::text, source_file_ids
        FROM esg_data_records
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND data_record_id=:data_record_id
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "data_record_id": data_record_id}).mappings().first()
    if not record:
        raise ApiError(404, "ESG_DATA_RECORD_NOT_FOUND", "ESG data record not found")
    sources = [
        {"source_type": "task_submission", "source_object_id": record["source_submission_id"], "target_object_type": "data_record", "target_object_id": data_record_id},
        {"source_type": "review", "source_object_id": record["source_task_id"], "target_object_type": "data_record", "target_object_id": data_record_id},
    ]
    for file_id in record["source_file_ids"] or []:
        sources.append({"source_type": "file", "source_object_id": str(file_id), "target_object_type": "data_record", "target_object_id": data_record_id})
    return ok({"sources": sources}, request_id=request.state.request_id)
