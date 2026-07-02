from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.audit.service import write_audit_log
from app.modules.auth.dependencies import require_permission
from app.modules.projects.router import _authorize_project

router = APIRouter(prefix="/api/v1/projects/{project_id}/esg-data-records", tags=["ESG数据"])


def _tenant_id(user: dict) -> str:
    return str(user["current_tenant_id"])


def promote_submission_to_esg_data_records(
    db: Session,
    *,
    tenant_id: str,
    enterprise_id: str,
    project_id: str,
    task_id: str,
    submission_id: str,
) -> int:
    """Materialize approved task submission items into formal ESG data records.

    The source task/submission are part of the uniqueness boundary so re-reviewing an
    approved task is idempotent and never creates duplicate formal data rows.
    """
    db.execute(
        text(
            """
            DELETE FROM esg_data_records
            WHERE tenant_id=:tenant_id
              AND project_id=:project_id
              AND source_task_id=:task_id
              AND source_submission_id=:submission_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "task_id": task_id,
            "submission_id": submission_id,
        },
    )
    result = db.execute(
        text(
            """
            INSERT INTO esg_data_records (
              tenant_id, enterprise_id, project_id, project_topic_id, project_topic_metric_id,
              topic_code, topic_name, metric_code, metric_name, data_type, value, text_value,
              unit, period, org_unit_id, org_unit_name, source_task_id, source_submission_id,
              source_submission_item_id, source_file_ids, review_status, report_reference_status
            )
            SELECT
              :tenant_id, :enterprise_id, :project_id, pt.project_topic_id, ptm.project_topic_metric_id,
              pt.topic_code, pt.topic_name, ptm.metric_code, ptm.metric_name, ptm.data_type,
              tsi.value, tsi.text_value, COALESCE(tsi.unit, ptm.unit), tsi.period,
              tsi.org_unit_id, ou.org_unit_name, :task_id, :submission_id,
              tsi.submission_item_id, COALESCE(tsi.attachment_file_ids, '{}'::uuid[]),
              'approved', 'not_referenced'
            FROM task_submission_items tsi
            JOIN project_topic_metrics ptm
              ON ptm.tenant_id=tsi.tenant_id
             AND ptm.project_topic_metric_id=tsi.project_topic_metric_id
             AND ptm.project_id=tsi.project_id
            JOIN project_topics pt
              ON pt.tenant_id=ptm.tenant_id
             AND pt.project_topic_id=ptm.project_topic_id
             AND pt.project_id=ptm.project_id
            LEFT JOIN org_units ou
              ON ou.tenant_id=tsi.tenant_id
             AND ou.org_unit_id=tsi.org_unit_id
            WHERE tsi.tenant_id=:tenant_id
              AND tsi.project_id=:project_id
              AND tsi.submission_id=:submission_id
              AND (tsi.value IS NOT NULL OR NULLIF(tsi.text_value, '') IS NOT NULL)
            """
        ),
        {
            "tenant_id": tenant_id,
            "enterprise_id": enterprise_id,
            "project_id": project_id,
            "task_id": task_id,
            "submission_id": submission_id,
        },
    )
    return max(result.rowcount or 0, 0)


@router.get("")
def list_esg_data_records(
    project_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("project:read")),
    topic_code: str | None = None,
    metric_code: str | None = None,
    org_unit_id: str | None = None,
    period: str | None = None,
    data_type: str | None = None,
    source_task_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    _authorize_project(request, db, user, project_id)
    clauses = ["tenant_id=:tenant_id", "project_id=:project_id"]
    params: dict[str, object] = {"tenant_id": _tenant_id(user), "project_id": project_id, "limit": page_size, "offset": (page - 1) * page_size}
    for key, value in {
        "topic_code": topic_code,
        "metric_code": metric_code,
        "org_unit_id": org_unit_id,
        "period": period,
        "data_type": data_type,
        "source_task_id": source_task_id,
    }.items():
        if value:
            clauses.append(f"{key}=:{key}")
            params[key] = value
    where = " AND ".join(clauses)
    rows = db.execute(text(f"""
        SELECT data_record_id::text, project_id::text, topic_code, topic_name, metric_code, metric_name,
               data_type::text, value, text_value, unit, period, org_unit_id::text, org_unit_name,
               org_unit_name AS source_org_unit_name, source_task_id::text, source_submission_id::text,
               source_submission_item_id::text, source_file_ids, review_status::text, report_reference_status,
               created_at, updated_at
        FROM esg_data_records
        WHERE {where}
        ORDER BY topic_name, metric_name, period NULLS LAST, created_at DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    total = db.execute(text(f"SELECT count(*) FROM esg_data_records WHERE {where}"), params).scalar_one()
    return ok({"items": [dict(r) for r in rows], "page": page, "page_size": page_size, "total": total}, request_id=request.state.request_id)


@router.get("/{data_record_id}/sources")
def esg_data_record_sources(project_id: str, data_record_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    project = _authorize_project(request, db, user, project_id)
    row = db.execute(text("""
        SELECT data_record_id::text, source_task_id::text, source_submission_id::text,
               source_submission_item_id::text, source_file_ids, topic_name, metric_name
        FROM esg_data_records
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND data_record_id=:data_record_id
    """), {"tenant_id": _tenant_id(user), "project_id": project_id, "data_record_id": data_record_id}).mappings().first()
    if not row:
        raise ApiError(404, "ESG_DATA_RECORD_NOT_FOUND", "ESG data record not found")
    file_rows = db.execute(text("""
        SELECT file_id::text, file_name AS original_filename, mime_type, business_type, uploaded_at AS created_at
        FROM file_objects
        WHERE tenant_id=:tenant_id
          AND enterprise_id=:enterprise_id
          AND project_id=:project_id
          AND file_id = ANY(:file_ids)
        ORDER BY uploaded_at DESC
    """), {
        "tenant_id": _tenant_id(user),
        "enterprise_id": project["enterprise_id"],
        "project_id": project_id,
        "file_ids": row["source_file_ids"] or [],
    }).mappings().all()
    return ok({"sources": [{"source_type": "collection_task", **dict(row), "files": [dict(r) for r in file_rows]}]}, request_id=request.state.request_id)


@router.patch("/{data_record_id}/report-reference-status")
def update_report_reference_status(project_id: str, data_record_id: str, payload: dict, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    status = payload.get("report_reference_status")
    if status not in {"not_referenced", "referenced", "needs_review", "superseded"}:
        raise ApiError(400, "ESG_DATA_REFERENCE_STATUS_INVALID", "Invalid report reference status")
    result = db.execute(text("""
        UPDATE esg_data_records
        SET report_reference_status=:status, updated_at=now()
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND data_record_id=:data_record_id
    """), {"tenant_id": _tenant_id(user), "project_id": project_id, "data_record_id": data_record_id, "status": status})
    if result.rowcount == 0:
        raise ApiError(404, "ESG_DATA_RECORD_NOT_FOUND", "ESG data record not found")
    write_audit_log(db, tenant_id=_tenant_id(user), enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="esg_data.report_reference_status_updated", object_type="esg_data_records", object_id=data_record_id, description=f"更新ESG数据报告引用状态为 {status}", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    db.commit()
    return ok({"data_record_id": data_record_id, "report_reference_status": status}, request_id=request.state.request_id)
